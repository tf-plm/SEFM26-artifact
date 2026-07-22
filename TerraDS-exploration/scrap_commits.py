import sqlite3
import requests
import json
import os
import time
import argparse
import zipfile
import io
import tarfile
import shutil
from threading import Lock
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from tqdm import tqdm

DB_PATH = 'TerraDS.sqlite'
OUTPUT_BASE_DIR = 'module_data'
TOKEN_FILE = 'tokens.txt'

# Shard management
shard_counts = defaultdict(int)
shard_lock = Lock()

def load_tokens(filepath):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return []
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]

TOKENS = load_tokens(TOKEN_FILE)
MAX_WORKERS = min(len(TOKENS) * 3, 60) if TOKENS else 1
token_queue = Queue()
for t in TOKENS:
    token_queue.put({"key": t, "reset_at": 0})

def get_token():
    while True:
        token = token_queue.get()
        wait_time = token['reset_at'] - time.time()
        if wait_time > 0:
            token_queue.put(token)
            time.sleep(min(wait_time, 2))
            continue
        return token

def compress_and_cleanup(shard_id):
    """Compresses a shard directory and removes it."""
    shard_path = os.path.join(OUTPUT_BASE_DIR, str(shard_id))
    tar_path = f"{shard_path}.tar.gz"
    
    if os.path.exists(shard_path):
        print(f"\n[Shard {shard_id}] Compressing...")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(shard_path, arcname=os.path.basename(shard_path))
        
        if os.path.exists(tar_path):
            shutil.rmtree(shard_path)
            print(f"[Shard {shard_id}] Cleaned up.")

def fetch_module_history(module_info):
    module_id, repo_name, path = module_info
    shard_id = module_id // 1000
    shard_dir = os.path.join(OUTPUT_BASE_DIR, str(shard_id))
    module_dir = os.path.join(shard_dir, f"module_{module_id}")
    
    try:
        if not os.path.exists(module_dir):
            os.makedirs(module_dir, exist_ok=True)
            token = get_token()
            headers = {"Authorization": f"token {token['key']}", "Accept": "application/vnd.github+json"}

            commits_url = f"https://api.github.com/repos/{repo_name}/commits?path={path}&per_page=100"
            resp = requests.get(commits_url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                raw_commits = resp.json()
                history_meta = []
                for c in raw_commits:
                    sha = c['sha']
                    history_meta.append({"sha": sha, "author": c['commit']['author']['name'], "message": c['commit']['message']})
                    
                    # Fetch files
                    archive_url = f"https://api.github.com/repos/{repo_name}/zipball/{sha}"
                    arch_resp = requests.get(archive_url, headers=headers, timeout=20)
                    if arch_resp.status_code == 200:
                        with zipfile.ZipFile(io.BytesIO(arch_resp.content)) as z:
                            for zip_info in z.infolist():
                                rel_path = "/".join(zip_info.filename.split("/")[1:])
                                if rel_path.startswith(path) and rel_path.endswith(('.tf', '.tfvars')):
                                    ver_path = os.path.join(module_dir, "versions", sha)
                                    os.makedirs(ver_path, exist_ok=True)
                                    with open(os.path.join(ver_path, os.path.basename(rel_path)), "wb") as f:
                                        f.write(z.read(zip_info))

                with open(os.path.join(module_dir, "metadata.json"), "w") as f:
                    json.dump({"id": module_id, "repo": repo_name, "path": path, "history": history_meta}, f)
            
            token_queue.put(token)

    except Exception:
        pass
    finally:
        # Atomic decrement to check if shard is finished
        with shard_lock:
            shard_counts[shard_id] -= 1
            if shard_counts[shard_id] <= 0:
                compress_and_cleanup(shard_id)

def create_master_archive():
    master_filename = "all_module.tar"
    
    tar_files = [f for f in os.listdir(OUTPUT_BASE_DIR) if f.endswith('.tar.gz')]
    if not tar_files:
        return

    with tarfile.open(master_filename, "w") as master_tar:
        for filename in tqdm(tar_files, desc="Bundling shards"):
            file_path = os.path.join(OUTPUT_BASE_DIR, filename)
            master_tar.add(file_path, arcname=filename)
            os.remove(file_path)

    if not os.listdir(OUTPUT_BASE_DIR):
        os.rmdir(OUTPUT_BASE_DIR)
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=None)
    args = parser.parse_args()

    # SQL treatment: connect; find modules with no submodules
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT M.Id, R.FullName, M.Path FROM Modules M JOIN Repositories R ON M.RepositoryId = R.Id WHERE M.ModuleCalls == '[]'")
    targets = cursor.fetchall()
    conn.close()
    if args.num:
        targets = targets[:args.num]

    # Initialize shard counters for scalability
    for m in targets:
        shard_id = m[0] // 1000
        shard_counts[shard_id] += 1

    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    # Parallelize process
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(tqdm(executor.map(fetch_module_history, targets), total=len(targets), desc="Processing Shards"))
    # Create master acrhive
    create_master_archive()
    
if __name__ == "__main__":
    main()