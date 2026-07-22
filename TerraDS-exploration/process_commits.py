import tarfile
import os
import json
import hcl2
import argparse
import re
import shutil
import threading
import time
# import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from lark.exceptions import UnexpectedToken, LarkError

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


supported = ['aws', 'azurerm', 'google', 'kubernetes']
timeout_modules = []
tolarge_modules = []
no_metadata = []
immutables = {}
results = {}
case_counter = 0
TIMEOUT_LIMIT_MINUTES = 1
TIMEOUT_LIMIT = TIMEOUT_LIMIT_MINUTES * 60
results_lock = threading.Lock()  # Protects case_counter and results dict
tolarge_modules_lock = threading.Lock()
timeout_modules_lock = threading.Lock()
nometadata_modules_lock = threading.Lock()

LIMIT_RESOURCES = 50

# -----

class ExcessiveNumberOfResources(Exception):

    def __init__(self, count, message="Excessive number of resources detected"):
        self._number = count
        self.message = f"{message} (Count: {count})"
        super().__init__(self.message)

    def number(self) -> int:
        return self._number
    

class ProcessingTimeout(Exception):
    def __init__(self, module_path, timeout_limit=TIMEOUT_LIMIT):
        self.module_path = module_path
        self.message = f"Analysis of {module_path} aborted after {timeout_limit}s"
        super().__init__(self.message)

# -----

def load_immutables(immut_dir):
    if not os.path.exists(immut_dir):
        return
    for filename in os.listdir(immut_dir):
        if filename.startswith("terraform-provider-") and filename.endswith("-immutattrs.json"):
            parts = filename.split('-')
            provider = parts[2]
            with open(os.path.join(immut_dir, filename), 'r') as f:
                immutables[provider] = json.load(f)


def process_module_logic(module_path):
    metadata_file = os.path.join(module_path, "metadata.json")
    try:
        with open(metadata_file, 'r') as file:
            metadata = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # print(f"FILE {metadata_file} NOT FOUND")
        with nometadata_modules_lock: 
            no_metadata.append(module_path)
        return None

    # Filter: at least 2 versions required for comparison
    history = metadata.get("history", [])
    if len(history) < 2: 
        return None

    latest_sha = history[0]["sha"]
    latest_version_path = os.path.join(module_path, "versions", latest_sha)

    # Filter: ensure the module uses supported providers
    if not os.path.exists(latest_version_path) or not __check_providers(latest_version_path):  
        return None
    
    result = {
        "repository": metadata.get("repo", "unknown"),
        "module_path": metadata.get("path", "unknown"),
        "localpath": module_path,
        "changes": []
    }

    # Identify changes between versions
    changes = __check_changes(module_path, metadata)

    for (sha_old, resources_old, sha_new, resources_new, modified) in changes:
        modified_attributes = __get_crit_modification(modified)
        crit_changes = []
        # Build dependency graph for the studied version
        curr_version_path = os.path.join(module_path, "versions", sha_new)
        dep_graph = __make_graph(curr_version_path)

        for (provider, res_type, res_name, attr_name) in modified_attributes:
            # Check if change is immutable and part of a dependency chain
            if provider in immutables and res_type in immutables[provider]:
                if attr_name in immutables[provider][res_type]:
                    vertex_name = f"{res_type}.{res_name}"
                    if __has_dependence(dep_graph, vertex_name) or __is_dependent(dep_graph, vertex_name):
                        crit_changes.append((provider, res_type, res_name, attr_name))
        
        if crit_changes:
            dictchanges = {
                "sha_old": sha_old,
                "sha_new": sha_new,
                "number_of_resources": len(dep_graph.keys()),
                "resource_attributes" : [
                    {"provider": p, "type": rt, "name": rn, "attribute": an}
                    for (p, rt, rn, an) in crit_changes
                ]
            }
            result["changes"].append(dictchanges)
            if NUM_WORKER == 1:
                print(f"""
The module {module_path}, has critical changes.
Commit old: {sha_old}
Commit new: {sha_new}
Attributes with stability issues: {crit_changes}
""", flush=True)

    return result if result["changes"] else None

def _process_wrapper(module_path, queue):
    try:
        result = process_module_logic(module_path)
        queue.put({"status": "success", "data": result})
    except ExcessiveNumberOfResources as e:
        queue.put({
            "status": "excessive_resources", 
            "count": e.number(),
            "msg": str(e)
        })
    except Exception as e:
        queue.put({"status": "error", "msg": str(e)})

def _thread_safe_worker(module_path, shared_results):
    global case_counter
    analysis_result = None
    # print(f"[START] Process module {module_path}", flush=True)
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
            target=_process_wrapper, 
            args=(module_path, queue)
        )
    timeout = False
    proc.start()
    start_time = time.perf_counter()
    while proc.is_alive():
        curr_time = time.perf_counter()
        time.sleep(1)
        if curr_time - start_time > TIMEOUT_LIMIT:
            proc.terminate()
            proc.join()
            timeout = True
            with timeout_modules_lock:
                timeout_modules.append(module_path)
            print(f"[ABORT] Process module {module_path} exceeded {TIMEOUT_LIMIT_MINUTES} minutes ({TIMEOUT_LIMIT} seconds).", flush=True)
    if not timeout:
        if not queue.empty():
            response = queue.get()
            if response["status"] == "success":
                analysis_result = response["data"]
                # print("-----")
                # print(response)
                # print(analysis_result)
                # print("-----")
                # print(f"[END] Process module {module_path}", flush=True)
                if (analysis_result):
                    with results_lock:
                        shared_results[case_counter] = analysis_result
                        case_counter += 1
                        # print(shared_results)
                # print("-----")
            elif response["status"] == "excessive_resources":
                count = response["count"]
                with tolarge_modules_lock:
                    tolarge_modules.append(module_path)
                print(f"[SKIPPED] Excluded the module {module_path} because of its excessive number of ressources ({count}).", flush=True)
            else:
                pass # Any other error

    # proc.join(timeout=TIMEOUT_LIMIT)
    # analysis_result = None 
    # if proc.is_alive():
    #     print(f"[ABORT] Process module {module_path} exceeded {TIMEOUT_LIMIT_MINUTES} minutes ({TIMEOUT_LIMIT} seconds).", flush=True)
    #     timeout_modules.append(module_path)
    #     proc.terminate()
    #     proc.join()
    # else:
    #     if not queue.empty():
    #         response = queue.get()
    #         if response["status"] == "success":
    #             analysis_result = response["data"]
    #             # print(f"[END] Process module {module_path}", flush=True)
    #             with results_lock:
    #                 shared_results[case_counter] = analysis_result
    #                 case_counter += 1
    #         elif response["status"] == "excessive_resources":
    #             count = response["count"]
    #             tolarge_modules.append(module_path)
    #             print(f"[SKIPPED] Excluded the module {module_path} because of its excessive number of ressources ({count}).", flush=True)
    #         else:
    #             pass
                # print(f"[ERROR] {module_path}: {response['msg']}", flush=True)


def __make_graph(tf_path):
    resources = __make_resource_dict(tf_path)
    all_resource_ids = [f"{t}.{n}" for (t, n) in resources.keys()]
    graph = {res_id: set() for res_id in all_resource_ids}

    for (res_type, res_name), attrs in resources.items():
        current_id = f"{res_type}.{res_name}"
        
        # Explicit depends_on
        explicit = attrs.get('depends_on', [])
        for dep in explicit:
            clean_dep = re.sub(r'^\${|}$', '', dep).split('.')[0:2]
            dep_id = ".".join(clean_dep)
            if dep_id in graph:
                graph[current_id].add(dep_id)

        # Implicit references
        def find_references(data):
            if isinstance(data, str):
                for target in all_resource_ids:
                    if re.search(rf'\b{re.escape(target)}\b', data):
                        if target != current_id:
                            graph[current_id].add(target)
            elif isinstance(data, dict):
                for val in data.values(): find_references(val)
            elif isinstance(data, list):
                for item in data: find_references(item)
        find_references(attrs)
    return graph


def __has_dependence(graph, resource):
    return len(graph.get(resource, set())) > 0


def __is_dependent(graph, resource):
    for target_set in graph.values():
        if resource in target_set: return True
    return False


def __get_crit_modification(modified_dict):
    criticals = []
    for (res_type, res_name), data in modified_dict.items():
        old_attrs, new_attrs = data['old'], data['new']
        try:
            provider = res_type.split('_')[0]
            all_keys = set(old_attrs.keys()) | set(new_attrs.keys())
            for attr_name in all_keys:
                if old_attrs.get(attr_name) != new_attrs.get(attr_name):
                    criticals.append((provider, res_type, res_name, attr_name))
        except Exception: pass
    return criticals


def __make_resource_dict(path):
    aggregated_resources = {}
    if not os.path.exists(path): return aggregated_resources
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if file.endswith(".tf") and os.path.isfile(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = hcl2.load(f)
                    if 'resource' in content:
                        for resource_block in content['resource']:
                            if len(resource_block.items()) > LIMIT_RESOURCES:
                                tolarge_modules.append(path)
                                raise ExcessiveNumberOfResources(len(resource_block.items()))
                            for res_type, res_map in resource_block.items():
                                for res_name, attributes in res_map.items():
                                    aggregated_resources[(res_type, res_name)] = attributes              
            except (UnexpectedToken, LarkError): pass
    return aggregated_resources


def __compare_resources(old_res, new_res):
    # Resources added in the new version
    added = {k: new_res[k] for k in new_res if k not in old_res}
    # Resources removed in the new version
    removed = {k: old_res[k] for k in old_res if k not in new_res}
    # Resources that exist in both but have different attribute
    modified = {
        k: {"old": old_res[k], "new": new_res[k]}
        for k in old_res.keys() & new_res.keys()
        if old_res[k] != new_res[k] # TODO Check if we want to do deep diff 
    }
    return added, removed, modified

def __check_changes(module_path, metadata):
    res = []
    history = metadata.get("history", [])
    for i in range(len(history) - 1):
        v_new, v_old = history[i]["sha"], history[i + 1]["sha"]
        p_new = os.path.join(module_path, "versions", v_new)
        p_old = os.path.join(module_path, "versions", v_old)
        try:
            r_new, r_old = __make_resource_dict(p_new), __make_resource_dict(p_old)
            _, _, modified = __compare_resources(r_old, r_new)
            if modified:
                res.append((v_old, r_old, v_new, r_new, modified))
        except FileNotFoundError: pass
    return res


def __check_providers(version_path):
    for file_name in os.listdir(version_path):
        if file_name.endswith(".tf"):
            with open(os.path.join(version_path, file_name), 'r') as f:
                try:
                    hcl_dict = hcl2.load(f)
                    # Check terraform required_providers
                    if 'terraform' in hcl_dict:
                        for tf_block in hcl_dict['terraform']:
                            req_p = tf_block.get('required_providers', [{}])[0]
                            for _, details in req_p.items():
                                source = details.get('source', '')
                                # Check if supported strings are in the source
                                if not any(s in source for s in supported): return False
                    # Check direct provider blocks
                    if 'provider' in hcl_dict:
                        for p_block in hcl_dict['provider']:
                            for p_name in p_block.keys():
                                if p_name not in supported: return False
                except Exception: continue
    return True


def __process_nested_archives(main_tar_path, NUM_WORKER=8):
    main_dir = main_tar_path.replace(".tar.gz", "").replace(".tar", "")
    with tarfile.open(main_tar_path, 'r') as main_tar:
        main_tar.extractall(path=main_dir, filter="data")
    
    for root, dirs, files in os.walk(main_dir):
        number_of_files = len([f for f in files if not f.startswith(".") and f.endswith((".tar.gz", ".tar"))])
        chunk_count = 0

        
        for file in files:
            if not file.startswith(".") and (file.endswith(".tar.gz") or file.endswith(".tar")):
                file_path = os.path.join(root, file)
                chunk_dir = file_path.replace(".tar.gz", "").replace(".tar", "")     
                print(f"[START] Chunk {chunk_dir}", flush=True)
    
                with tarfile.open(file_path, 'r') as sub_tar:
                    sub_tar.extractall(path=root, filter="data")

                # Identify all module directories in this chunk
                module_paths = [
                    os.path.join(chunk_dir, d) 
                    for d in os.listdir(chunk_dir) 
                    if os.path.isdir(os.path.join(chunk_dir, d))
                ]

                # Parallelize
                with ThreadPoolExecutor(max_workers=NUM_WORKER) as executor:
                    executor.map(lambda p: _thread_safe_worker(p, results), module_paths)
                    chunk_count = chunk_count + 1
                    percent = (chunk_count / number_of_files) * 100
                shutil.rmtree(chunk_dir)
                print(f"[END] Chunk {chunk_dir}\n====== {percent:.2f} % of the total process ======", flush=True)

                
    shutil.rmtree(main_dir)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treat commits from a .tar file")
    parser.add_argument("-nw", "--num_workers", type=int, default=8, 
                        help="Number of workers (défaut: 8)")
    parser.add_argument("-tar", "--tar_file", type=str, default="all_module.tar", 
                        help="Tar file to analyze (default: all_module.tar)")
    parser.add_argument("-dir", "--immut_dir", type=str, default="immut-export", 
                        help="Directory of immuts (default: immut-export)")

    args = parser.parse_args()
    IMMUT_DIR = args.immut_dir
    TAR_FILE = args.tar_file
    NUM_WORKER = args.num_workers

    print(f"Running with : {TAR_FILE} ({NUM_WORKER} workers)", flush=True)

    load_immutables(IMMUT_DIR)
    final_results = __process_nested_archives(TAR_FILE, NUM_WORKER)

    with open("critical_changes.json", "w") as f:
        json.dump(final_results, f, indent=4)

    print(f"Too long modules to analyze (> {TIMEOUT_LIMIT_MINUTES} minutes): ", len(timeout_modules), flush=True)
    print(f"Too big modules to analyze  (> {LIMIT_RESOURCES} resources): ",     len(tolarge_modules), flush=True)
    print(f"Modules that appear empty (dunno why): ",     len(no_metadata), flush=True)
