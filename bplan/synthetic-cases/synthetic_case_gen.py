from itertools import combinations
from enum import Enum

import subprocess
import os
import sys
import itertools
import shutil
import json
import random
import argparse

PROVIDER = "example/myprovider"
TYPE_RESOURCE = "myprovider_simple"

NRESOURCE = 4

class Operation(str, Enum):
    CREATE        = "CREATE"
    DELETE        = "DELETE"
    UPDATE        = "UPDATE"
    CREATE_DELETE = "CREATE_DELETE"
    DELETE_CREATE = "DELETE_CREATE"
    NOOP          = "NOOP"

    @classmethod
    def all(cls):
        return [op for op in cls]

    @classmethod
    def replaces(cls):
        return [cls.DELETE_CREATE, cls.CREATE_DELETE]

    @classmethod
    def diffs(cls):
        return [cls.NOOP, cls.UPDATE, cls.DELETE_CREATE, cls.CREATE_DELETE]
    # FIXME add diffs_with_leading()

    @classmethod
    def diffs_with_leading(cls, op):
        ops = Operation.diffs()
        ops.remove(op)
        return [op] + ops

    @classmethod
    def diff_change(cls):
        return [cls.UPDATE, cls.DELETE_CREATE, cls.CREATE_DELETE]

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.name


class Resource:
    def __init__(self, name: str):
        self.__name = name

    @property
    def name(self) -> str:
        return self.__name

    def __eq__(self, o):
        return isinstance(o, Resource) and self.__name == o.name

    def __hash__(self):
        return hash(self.__name)

    def __repr__(self):
        return f"{self.__name}"

    def __iter__(self):
        return iter(self.name)

    def __mk_dependence(self, dependencies):
        deps = []
        for dep in dependencies:
            if dep.A == self:
                deps.append(dep.B)
        if deps == []:
            return ""
        else:
            fdeps = ',\n'.join(map(lambda dep: f"{TYPE_RESOURCE}.{dep.name}", deps))
            return f""",
      "depends_on": [
          "{fdeps}"
      ]"""

    def tfstate(self, dependencies):
        return f"""
{{
      "address": "{TYPE_RESOURCE}.{self.name}",
      "mode": "managed",
      "type": "{TYPE_RESOURCE}",
      "name": "{self.name}",
      "provider_name": "registry.terraform.io/{PROVIDER}",
      "schema_version": 0,
      "values": {{
        "name": "{self.name}"
      }} {self.__mk_dependence(dependencies)}
}}
"""


class Dependence:
    def __init__(self, A: Resource, B: Resource):
        self.A = A
        self.B = B

    def __str__(self):
        return f"{self.A.name} depends on {self.B.name}"

    def __repr__(self):
        return f"{self.A.name}->{self.B.name}"


def has_cycle(resources: set, deps: list[Dependence]) -> bool:
    # build adjacency list
    adj = {r: [] for r in resources}
    for dep in deps:
        adj[dep.A].append(dep.B)

    visited = set()
    stack = set()

    def dfs(node):
        if node in stack:
            return True  # cycle
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for neigh in adj.get(node, []):
            if dfs(neigh):
                return True
        stack.remove(node)
        return False

    return any(dfs(r) for r in resources)

def validate_case(
    state_resources: set[Resource],
    state_deps: list[Dependence],
    target_resources: set[Resource],
    target_deps: list[Dependence],
    operations: dict[Resource, Operation] 
) -> bool:
    """
    Return 0 if valid, otherwise return the errorcode:
    1. Every dependency references existing resources in its graph.
    2. If operations is provided, it matches the exact change in membership:
        * DELETE  <=> resource removed (ie in state, but not in target)
        * CREATE  <=> resource added (ie not in state, but in target)
        * UPDATE / CREATE_DELETE / DELETE_CREATE / NOOP <=> resource unchanged
    3. No cycles.
    """
    # --- 1. dependency ---
    for dep in state_deps:
        if dep.A not in state_resources or dep.B not in state_resources:
            return 1
    for dep in target_deps:
        if dep.A not in target_resources or dep.B not in target_resources:
            return 1

    # --- 2. operations consistency ---
    if operations is not None:
        # Every resource that appears anywhere must have an operation entry
        # Hint : It can NOOP
        for r in state_resources | target_resources:
            if r not in operations:
                return 2

        for r, op in operations.items():
            in_state = r in state_resources
            in_target = r in target_resources

            if op == Operation.DELETE:
                if not (in_state and not in_target):
                    return 2
            elif op == Operation.CREATE:
                if not (not in_state and in_target):
                    return 2
            elif op in (Operation.UPDATE,
                        Operation.CREATE_DELETE,
                        Operation.DELETE_CREATE,
                        Operation.NOOP):
                if not (in_state and in_target):
                    print("HERE")
                    return 2
            else:
                return 2

        # --- 3. Cycle detection ---
        if has_cycle(state_resources, state_deps):
            return 3
        if has_cycle(target_resources, target_deps):
            return 3

    return 0

class Case:

    def __init__(self, state_resources: set[Resource], state_deps: list[Dependence], 
                 target_resources: set[Resource], target_deps: list[Dependence],
                 operations: dict[Resource, Operation] = None, validate = False):
        if validate:
            assert(validate_case(state_resources, state_deps, target_resources,target_deps, operations))
        # convert list to set if needed
        if type(state_resources) == list:
            self.__state_resources = set(state_resources)
        else:    
            self.__state_resources = state_resources
        # convert list to set if needed 
        if type(target_resources) == list:
            self.__target_resources = set(target_resources)
        else:    
            self.__target_resources = target_resources
        self.__operations = operations
        self.__state_deps = state_deps
        self.__target_deps = target_deps

    def is_valid(self) -> bool :
        return 0 == validate_case(self.state_resources, self.state_deps,
                                  self.target_resources, self.target_deps,
                                  self.operations)

    @property
    def target_resources(self) -> set[Resource]:
        return self.__target_resources

    @property
    def state_resources(self) -> set[Resource]:
        return self.__state_resources

    @property
    def operations(self) -> dict[Resource, Operation]:
        return self.__operations

    @property
    def state_deps(self) -> list[Dependence]:
        return self.__state_deps

    @property
    def target_deps(self) -> list[Dependence]:
        return self.__target_deps

    def print_oneline(self):
        return f"{self.__state_resources}, {self.__target_resources}, {self.__operations}, {self.__state_deps}, {self.__target_deps}"

    def __str__(self):
        ops = '\n'.join(f"{r}: {op}" for r, op in self.__operations.items())
        return f"State resources: {self.__state_resources} \nState graph: {self.__state_deps} \nTarget resources: {self.__target_resources} \nTarget graph: {self.__target_deps} \nwith\n{ops}"


# ----------

    def hcl(self, mode="state"):
        resources = []
        # -------
        if mode == "state":
            mode_resources = self.state_resources
            mode_graph = self.state_deps
        elif mode == "target":
            mode_resources = self.target_resources
            mode_graph = self.target_deps
        # --------
        for resource in mode_resources:
            deps = []
            suffix_value = ""
            lifecycle = "lifecycle { }"
            if mode == "target" and self.operations[resource] in [Operation.CREATE_DELETE, Operation.UPDATE, Operation.DELETE_CREATE]:
                suffix_value += "_new"
                if self.operations[resource] == Operation.CREATE_DELETE:
                    lifecycle = """
    lifecycle {
        create_before_destroy = true
    }
"""
            for dependency in mode_graph:
                if dependency.A == resource:
                    deps.append(dependency.B)
            resources.append(f"""
resource "myprovider_simple" "{resource.name}" {{ 
    name = "{resource.name}{suffix_value}"  
    depends_on = [{', '.join(map(lambda r: TYPE_RESOURCE + "." + r.name, deps))}]
    {lifecycle}
}}
""")   
        hcl_resources = '\n'.join(resources)
        return f"""
terraform {{
  required_providers {{
    myprovider = {{
      source = "example/myprovider"
    }}
    }}
}}

provider "myprovider" {{}}

{hcl_resources}
"""

# ----------

    def tfstate(self):
        resources = ',\n'.join([res.tfstate(self.state_deps) for res in self.state_resources])
        return f"""
{{
  "version": 4,
  "terraform_version": "1.13.3",
  "values" : {{
    "outputs": {{ }},
    "root_module": {{
      "resources": [
        {resources}
      ]
    }}
  }},
  "check_results": null
}}"""


    def plan_json(self):
        # --- prior_state (before plan) ---
        prior_resources = []
        for res in self.state_resources:
            address = f"{TYPE_RESOURCE}.{res.name}"
            values = {"name": res.name}

            deps = [ f"{TYPE_RESOURCE}.{d.B.name}" for d in self.state_deps if d.A == res ]

            prior_resources.append({
                "address": address,
                "mode": "managed",
                "type": TYPE_RESOURCE,
                "name": res.name,
                "provider_name": f"registry.terraform.io/{PROVIDER}",
                "schema_version": 0,
                "values": values,
                "sensitive_values": {},
                "depends_on": deps,
            })

        prior_state = {
            "format_version": "1.0",
            "terraform_version": "1.5.7",
            "values": {
                "root_module": {
                    "resources": prior_resources
                }
            }
        }

        # --- planned_values (after plan) ---
        resources = []
        resource_changes = []
        config_resources = []

        for res in self.target_resources:
            address = f"{TYPE_RESOURCE}.{res.name}"
            values = {"name": res.name}

            deps = [ f"{TYPE_RESOURCE}.{d.B.name}" for d in self.target_deps if d.A == res ]
            # deps = []
            # if res in self.target_deps:
            #     deps = [f"{TYPE_RESOURCE}.{d.name}" for d in self.target_deps[res]]

            resources.append({
                "address": address,
                "mode": "managed",
                "type": TYPE_RESOURCE,
                "name": res.name,
                "provider_name": f"registry.terraform.io/{PROVIDER}",
                "depends_on": deps,
                "values": values,
            })

            # decide actions based on operations
            op = self.operations.get(res)
            if op == Operation.CREATE:
                actions, before, after = ["create"], None, values
            elif op == Operation.DELETE:
                actions, before, after = ["delete"], values, None
            elif op == Operation.CREATE_DELETE:
                actions, before, after = ["create", "delete"], values, values
            elif op == Operation.DELETE_CREATE:
                actions, before, after = ["delete", "create"], values, values
            elif op == Operation.UPDATE or op == Operation.NOOP:
                actions, before, after = [op.lower()], values, values
            else:
                raise Exception("unknown operation", op)

            resource_changes.append({
                "address": address,
                "mode": "managed",
                "type": TYPE_RESOURCE,
                "name": res.name,
                "provider_name": f"registry.terraform.io/{PROVIDER}",
                "change": {
                    "actions": actions,
                    "before": before,
                    "after": after,
                }
            })

            config_resources.append({
                "address": address,
                "mode": "managed",
                "type": TYPE_RESOURCE,
                "name": res.name,
                "provider_config_key": "myprovider",
                "expressions": {
                    "name": {
                        "constant_value": res.name
                    }
                },
                "depends_on": deps,
            })

        # --- full plan ---
        plan = {
            "format_version": "1.1",
            "terraform_version": "1.5.7",
            "prior_state": prior_state,
            "planned_values": {"root_module": {"resources": resources}},
            "resource_changes": resource_changes,
            "configuration": {
                "provider_config": {
                    "myprovider": {
                        "name": "myprovider",
                        "full_name": f"registry.terraform.io/{PROVIDER}"
                    }
                },
                "root_module": {"resources": config_resources}
            }
        }

        return json.dumps(plan, indent=2)



# def mkDependenceCases(resources: list[Resource]):
#     n = len(resources)
#     # For each unordered pair (i<j) we have three choices:
#     #   0: no edge
#     #   1: i->j
#     #   2: j->i
#     # That’s 3^(n combinaison 2) total configurations.
#     pairs = list(combinations(resources, 2))
#     num_pairs = len(pairs)
#     total = 3 ** num_pairs
#     all_cases = []
#     for mask in range(total):
#         case = []
#         m = mask
#         for i, (a, b) in enumerate(pairs):
#             choice = m % 3
#             m //= 3
#             if choice == 1:
#                 case.append(Dependence(a, b))
#             elif choice == 2:
#                 case.append(Dependence(b, a))
#         all_cases.append(case)
#     return all_cases

def generate_all_topologies(resources):
    """
    returns all sets of Dependence A->B with their index in the input such that index(A) < index(B)
    """
    n = len(resources)
    dependency_options = []

    for i in range(n):
        for j in range(i + 1, n): 
            pair_options = [
                [], 
                [Dependence(resources[i], resources[j])], 
            ]
            dependency_options.append(pair_options)

    all_combinations = itertools.product(*dependency_options)
    topologies = [set(itertools.chain(*combination)) for combination in all_combinations ]
    return topologies

def all_dependence_combinations(resources):
    possible_deps = list(itertools.permutations(resources, 2))
    res = []
    for r in range(len(possible_deps) + 1):
        for combo in itertools.combinations(possible_deps, r):
            deps_combo = set(Dependence(r1, r2) for r1, r2 in combo )
            res.append(deps_combo)
    return [ ds for ds in res if not has_cycle(resources, list(ds)) ]

def generate_all_resource_operation_combinations(resources: list[Resource], operations: list[str]):
    if not resources:
        return [[]]
    resource_operation_options = []
    for resource in resources:
        resource_ops = [(resource, op) for op in operations]
        resource_operation_options.append(resource_ops)
    all_combinations = itertools.product(*resource_operation_options)
    return all_combinations

def all_resource_combinations(resources):
    """ returns list of sets in the the powerset """
    res = []
    for r in range(len(resources) + 1):
        for combo in itertools.combinations(resources, r):
            res.append(set(combo))
    return res


def run_terraform_apply(case_dir: str, case: Case, keeptrace=False):
    cmdline = ["time", "terraform", "apply", "-no-color", "-auto-approve", "-parallelism=8"]
    for replace in map(lambda rname : f"-replace={TYPE_RESOURCE}.{rname}", 
                       [res.name for (res, op) in case.operations.items() 
                        if op in (Operation.CREATE_DELETE, Operation.DELETE_CREATE)]):
        cmdline.append(replace)

    try:
        result = subprocess.run(
            cmdline,
            cwd=case_dir,
            capture_output=True,
            text=True,
            check=True
        )
        if keeptrace:
            hclpath = os.path.join(case_dir, "trace.txt")
            with open(hclpath, "w") as f:
                f.write(result.stdout)

    except subprocess.CalledProcessError as e:
        if e.stderr:
            if e.stderr.find("Error: Cycle:") > 0:
                print("CYCLE at ", case_dir, " found by Terraform command: ", ' '.join(cmdline))
                return
        print("CMD failure for case ", case_dir, ":", ' '.join(cmdline))
        print("stdout:\n", e.stdout)
        print("stderr:\n", e.stderr)
        raise e


def run_terraform_plan(case_dir, case):
    cmdline = ["terraform", "plan", "-no-color", "-out=plan.tfplan"]
    for replace in map(lambda rname : f"-replace={TYPE_RESOURCE}.{rname}", 
                       [res.name for (res, op) in case.operations.items() 
                        if op in (Operation.CREATE_DELETE, Operation.DELETE_CREATE)]):
        cmdline.append(replace)

    try:
        # 1. terraform plan -out=plan.tfplan
        subprocess.run(
            cmdline,
            cwd=case_dir,
            capture_output=True,
            text=True,
            check=True
        )
        # 2. terraform show -json plan.tfplan > tfplan.json
        out_file = os.path.join(case_dir, "tfplan.json")
        with open(out_file, "w") as f:
            subprocess.run(
                ["terraform", "show", "-json", "plan.tfplan"],
                cwd=case_dir,
                stdout=f,
                check=True
            )
    except subprocess.CalledProcessError as e:
        if e.stderr:
            if e.stderr.find("Error: Cycle:") > 0:
                print("CYCLE at ", case_dir, " found by Terraform command: ", ' '.join(cmdline))
                return
        print("CMD failure for case ", case_dir, ":", ' '.join(cmdline))
        print("stdout:\n", e.stdout)
        print("stderr:\n", e.stderr)
        raise e


def typical_case():
    rA = Resource("A")
    rB = Resource("B")
    rC = Resource("C")
    sr = set([rA, rB, rC])
    sg = [Dependence(rA, rB), Dependence(rA, rC), Dependence(rB, rC)]
    tr = set([rA, rB, rC])
    tg = [Dependence(rB, rA), Dependence(rC, rA), Dependence(rC, rB)]
    op = [(rA, Operation.UPDATE), (rB, Operation.UPDATE), (rC, Operation.CREATE_DELETE)]
    return Case(sr, sg, tr, tg, op, validate=False)

def run_a_case(my_case, dir, case_counter=-1):
    if not my_case.is_valid():
        print("Invalid case, skipping")
        return

    subdir = dir if case_counter < 0 else os.path.join(dir, f"{case_counter}")
    # Name of the generated directory for this case
    # subdir = os.path.join(dir, \
    #                         "-".join([ f"{r}_{op}" for r, op in my_case.operations.items() ]) + \
    #                         f"-{case_counter}")
    os.makedirs(subdir)

    # -- desc case in case.txt ---
    casepath = os.path.join(subdir, "case.txt")
    with open(casepath, "w") as f:
        f.write(f"case {case_counter}\n{my_case}\n")
    # -- write first main.tf ---
    hclpath = os.path.join(subdir, "main.tf")
    with open(hclpath, "w") as f:
        f.write(my_case.hcl(mode="state"))
    # -- terraform apply ---
    run_terraform_apply(subdir, my_case)
    # -- copy tfstate ---
    src = os.path.join(subdir, "terraform.tfstate")
    dst = os.path.join(subdir, "terraform.tfstate.old")
    shutil.copyfile(src, dst)
    # -- write second main.tf ---
    src = os.path.join(subdir, "main.tf")
    dst = os.path.join(subdir, "main.tf.old")
    shutil.copyfile(src, dst)
    hclpath = os.path.join(subdir, "main.tf")
    with open(hclpath, "w") as f:
        f.write(my_case.hcl(mode="target"))
    # -- terraform plan -out ---
    run_terraform_plan(subdir, my_case)
    # -- terraform apply ---
    run_terraform_apply(subdir, my_case, keeptrace=True)


def run_same_systematic_topological_cases(output_path, n):
    """
    Similar to run_systematic_topological_cases(n) but use the same graph as target and state,
    Skip disconnected graphs.
    """

    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    case_counter = 1

    resources = [Resource(chr(ord('A') + i)) for i in range(n)]
    resources.sort(key=lambda r: r.name[0])
    for state_deps in generate_all_topologies(resources):

        # skip disconnected graphs
        if len(set(r for dep in state_deps for r in [dep.A, dep.B])) != len(resources):
            print(f"Skipping {state_deps}")
            continue

        state_resources = resources
        target_resources = resources
        target_deps = state_deps

        # operations
        for diff_op_combo in generate_all_resource_operation_combinations(resources, Operation.diffs()):
            diff_op_combo_dict = dict(diff_op_combo)
            op_map = { r:diff_op_combo_dict[r] for r in resources }
            if all(op == Operation.NOOP for op in op_map.values()):
                # skip only NOOPs
                continue

            # case
            my_case = Case(state_resources, state_deps, target_resources, target_deps, op_map)
            assert my_case.is_valid(), "Invalid case"

            case_name = '-'.join(f"{r}_{op}" for r, op in op_map.items()) + f"-{case_counter}"
            case_output_path = os.path.join(output_path, case_name)
            print(case_name)
            run_a_case(my_case, case_output_path)

            case_counter += 1

    print(f"{case_counter} cases.")
    return

def run_systematic_topological_cases(output_path, n):
    """
    Generated cases have the following properties
    * either the target or the state graphs have n resources, the other one may have <n resources
    * one set of dependency arcs is the subset of the other, arcs addition/removal corresponds to node creation/deletion, there is no "changed" arc
    """

    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    case_counter = 1

    # resource nodes
    resources_n = [Resource(chr(ord('A') + i)) for i in range(n)]
    resources_ltns = list(list(ltns) for k in range(n) for ltns in itertools.combinations(resources_n, k))
    all_deps = generate_all_topologies(resources_n)

    # pairs of (target, state) resource nodes
    resources_pairs_create = list(itertools.product(resources_ltns, [resources_n]))
    resources_pairs_delete = list(itertools.product([resources_n], resources_ltns))
    resources_pair_same = (resources_n,resources_n)

    def remove_res_not_in(rs1, rs2):
        return [r1 for r1 in rs1 if r1 not in rs2]

    def remove_deps_not_in(deps: [Dependence], rs):
        return [dep for dep in deps if dep.A in rs and dep.B in rs]

    # for state_resources, target_resources in [resources_pair_same]:
    for state_resources, target_resources in resources_pairs_create + resources_pairs_delete + [resources_pair_same]:

        # operations
        ress = list(target_resources + state_resources)
        ress.sort(key=lambda r: r.name[0])
        create_ops = { r: Operation.CREATE for r in remove_res_not_in(target_resources, state_resources) }
        delete_ops = { r: Operation.DELETE for r in remove_res_not_in(state_resources, target_resources) }
        diff_res = set(target_resources) & set(state_resources)
        for diff_op_combo in generate_all_resource_operation_combinations(diff_res, Operation.diffs()):
            op_map_unordered = { **dict(diff_op_combo), **create_ops, **delete_ops }
            op_map = { r:op_map_unordered[r] for r in ress }
            if all(op == Operation.NOOP for op in op_map.values()):
                # skip only NOOPs
                continue

            # deps
            if len(target_resources) == n and len(state_resources) < n:
                # state subset of target
                all_state_deps = [remove_deps_not_in(deps, state_resources) for deps in all_deps]
                all_target_deps = all_deps
            elif len(state_resources) == n and len(target_resources) < n:
                # target subset of state
                all_state_deps = all_deps
                all_target_deps = [remove_deps_not_in(deps, target_resources) for deps in all_deps]
            else:
                # state and target same
                all_state_deps = all_target_deps = all_deps
            for state_deps, target_deps in zip(all_state_deps, all_target_deps):

                my_case = Case(state_resources, state_deps, target_resources, target_deps, op_map)
                assert my_case.is_valid(), "Invalid case"

                case_name = '-'.join(f"{r}_{op}" for r, op in op_map.items()) + f"-{case_counter}"
                case_output_path = os.path.join(output_path, case_name)
                print(f"Trying to run_a_case {case_counter} in {case_output_path}\n{my_case}")
                run_a_case(my_case, case_output_path)
                # print(case_name)

                case_counter += 1

    return


def gen_scalable_topology(layers=[1], connectivity=[], balance=False):
    topology_deps = []

    assert(len(layers) > 0)
    assert(len(connectivity) == len(layers)-1)

    ord_ressources = {}
    dep_ressource = {}
    layer_ressources = []
    # layer_letter = 'A'

    # I - First generate all ressources
    # with name : letter for layer + horizontal position 
    for i in range(len(layers)):
        curr_layer = [Resource(f"R{i}_{j}") for j in range(layers[i])]
        ord_ressources.update({r: 0 for r in curr_layer}) # ord_ressource[A] = in_edge(A) + in_edge(B)
        dep_ressource.update({r: [] for r in curr_layer}) # dep_ressource[A] = all B | A -> B
        layer_ressources.append(curr_layer)
        # layer_letter = chr(ord(layer_letter) + 1)

    # II - Then generate edges
    for k in range(0, len(layer_ressources)-1):
        layer_0 = layer_ressources[k]
        layer_1 = layer_ressources[k+1]
        must_connect_in_layer_1 = [r for r in layer_1] 
        # 1 - ascending
        # for each R of layer_0: make an edge to a random element S of must_connect_in_layer_1
        # then remove S in must_connect_in_layer_1
        for R in layer_0:
            if must_connect_in_layer_1 != []:
                S = random.choice(must_connect_in_layer_1)
            else:
                min_value_1 = min(ord_ressources[r] for r in layer_1)
                candidates = [r for r in layer_1 if ord_ressources[r] == min_value_1]
                S = random.choice(candidates)
            topology_deps.append(Dependence(R, S))
            dep_ressource[R].append(S)
            ord_ressources[R] = ord_ressources[R]+1
            ord_ressources[S] = ord_ressources[S]+1
            if S in must_connect_in_layer_1:
                must_connect_in_layer_1.remove(S)

        # 2 - descending
        # for each S of must_connect_in_layer_1 : make an edge to an element S of layer_0 with min cardinality
        for S in must_connect_in_layer_1:
            min_value = min(ord_ressources[r] for r in layer_0)
            candidates = [r for r in layer_0 if ord_ressources[r] == min_value]
            R = random.choice(candidates)
            topology_deps.append(Dependence(R, S))
            dep_ressource[R].append(S)
            ord_ressources[R] = ord_ressources[R]+1
            ord_ressources[S] = ord_ressources[S]+1

        # 3 - Rest with density 
        max_edges = len(layer_0) * len(layer_1)
        new_max_edges = max_edges - max(len(layer_0), len(layer_1))
        rest_edges = connectivity[k] * new_max_edges

        # 4 - Generate these new rest_edges edges randomly between layer_0 and layer_1
        for _ in range(rest_edges):
            candidate_layer_0 = [r for r in layer_0 if len(dep_ressource[r]) != len(layer_1)]
            if balance:
                min_value_0 = min(ord_ressources[r] for r in layer_0)
                candidate_layer_0 = [r for r in candidate_layer_0 if ord_ressources[r] == min_value_0]
            R = random.choice(candidate_layer_0)
            candidate_layer_1 = [r for r in layer_1 if r not in dep_ressource[R]] 
            # all element in layer_1 such as there is no existing Dep with R, that is, all S such as S not in dep_ressource[R]
            if balance:
                min_value_1 = min(ord_ressources[r] for r in candidate_layer_1)
                candidate_layer_1 = [r for r in candidate_layer_1 if ord_ressources[r] == min_value_1]
            S = random.choice(candidate_layer_1)
            topology_deps.append(Dependence(R, S))
            dep_ressource[R].append(S)
            ord_ressources[R] = ord_ressources[R]+1
            ord_ressources[S] = ord_ressources[S]+1

    resources = set([R for Dep in topology_deps for R in [Dep.A, Dep.B]])
    return resources, topology_deps


def gen_simple_benchcase(n, principal_op, principal_op_percentage, top_changes_percentage):

    # number of resources must be even
    n = 2*(n//2)

    # get a global list of operations for both resource groups
    ops = Operation.diffs_with_leading(principal_op)
    secondary_ops_percentage = (100 - principal_op_percentage) // 3
    weights = [principal_op_percentage/100] + 3*[secondary_ops_percentage/100]
    global_op_choices = random.choices(ops, k=2*(n//2), weights=weights)

    # split change operations for both groups: remove all NOOPs ; split ; add NOOPs back ; shuffle
    global_change_ops = [ op for op in global_op_choices if op != Operation.NOOP ]
    split_index = int(len(global_change_ops) * top_changes_percentage / 100)
    top_change_ops = global_change_ops[:split_index]
    bot_change_ops = global_change_ops[split_index:]
    top_ops = top_change_ops + [Operation.NOOP]*(n//2 - len(top_change_ops))
    bot_ops = bot_change_ops + [Operation.NOOP]*(n//2 - len(bot_change_ops))
    random.shuffle(top_ops)
    random.shuffle(bot_ops)

    # if the result ended with only NOOPs, add a random change operation
    if all([op == Operation.NOOP for op in top_ops]):
        top_ops[0] = random.choice(Operation.diff_change())
    if all([op == Operation.NOOP for op in bot_ops]):
        bot_ops[0] = random.choice(Operation.diff_change())

    # compute the simple 2-stages topology
    top_resources, bot_resources = [], []
    resources, dependencies = [], []
    for i in range(n//2):
        RA = Resource(f"A{i}")
        RB = Resource(f"B{i}")
        D = Dependence(RA, RB)
        top_resources.append(RA)
        bot_resources.append(RB)
        resources.append(RA)
        resources.append(RB)
        dependencies.append(D)
    assert len(resources) == n, \
        "Bad construction of simple 2-stages topology"

    # construct the final operations map
    top_ops_map = dict(zip(top_resources, top_ops))
    bot_ops_map = dict(zip(bot_resources, bot_ops))
    op_map = top_ops_map | bot_ops_map

    return Case(resources, dependencies, resources, dependencies, op_map)


def gen_butterfly_benchcase(n, principal_op, principal_op_percentage, mid_op, top_changes_percentage):

    # get a global list of operations for both resource groups
    ops = Operation.diffs_with_leading(principal_op)
    secondary_ops_percentage = (100 - principal_op_percentage) // 3
    weights = [principal_op_percentage/100] + 3*[secondary_ops_percentage/100]
    global_op_choices = random.choices(ops, k=2*(n//2), weights=weights)

    # split change operations for both groups: remove all NOOPs ; split ; add NOOPs back ; shuffle
    global_change_ops = [ op for op in global_op_choices if op != Operation.NOOP ]
    split_index = int(len(global_change_ops) * top_changes_percentage / 100)
    top_change_ops = global_change_ops[:split_index]
    bot_change_ops = global_change_ops[split_index:]
    top_ops = top_change_ops + [Operation.NOOP]*(n//2 - len(top_change_ops))
    bot_ops = bot_change_ops + [Operation.NOOP]*(n//2 - len(bot_change_ops))
    random.shuffle(top_ops)
    random.shuffle(bot_ops)

    # if the result ended with only NOOPs, add a random change operation
    if all([op == Operation.NOOP for op in top_ops]):
        top_ops[0] = random.choice(Operation.diff_change())
    if all([op == Operation.NOOP for op in bot_ops]):
        bot_ops[0] = random.choice(Operation.diff_change())

    # get the topology and retrieve top, bottom and mid resources
    resources, dependencies = gen_scalable_topology([n//2, 1, n//2], [0,0])
    top_resources = [ R for R in resources if R.name.startswith("R2") ]
    bot_resources = [ R for R in resources if R.name.startswith("R0") ]
    mid_resource = [ R for R in resources if R.name.startswith("R1") ][0]   # there is only one
    assert len(top_resources) == len(bot_resources) == n//2, \
        "Bad extraction of top and bot groups from butterfly topology"

    # construct the final operations map
    top_ops_map = dict(zip(top_resources, top_ops))
    bot_ops_map = dict(zip(bot_resources, bot_ops))
    mid_op_map = {mid_resource: mid_op}
    op_map = top_ops_map | bot_ops_map | mid_op_map

    return Case(resources, dependencies, resources, dependencies, op_map)


def gen_diamond_benchcase(n, principal_op, principal_op_percentage, top_op, bot_op):

    # get a global list of operations for the middle resource group
    ops = Operation.diffs_with_leading(principal_op)
    secondary_ops_percentage = (100 - principal_op_percentage) // 3
    weights = [principal_op_percentage/100] + 3*[secondary_ops_percentage/100]
    mid_ops_choices = random.choices(ops, k=n, weights=weights)

    # if the result ended with only NOOPs, add a random change operation
    if all([op == Operation.NOOP for op in mid_ops_choices]):
        mid_ops_choices[0] = random.choice(Operation.diff_change())

    # get the topology and retrieve top, bottom and mid resources
    resources, dependencies = gen_scalable_topology([1, n, 1], [0,0])
    top_resource = [ R for R in resources if R.name.startswith("R2") ][0]   # there is only one
    bot_resource = [ R for R in resources if R.name.startswith("R0") ][0]   # there is only one
    mid_resources = [ R for R in resources if R.name.startswith("R1") ]
    assert len(mid_resources) == n, \
        "Bad extraction of middle group from diamond topology"

    # construct the final operations map
    top_op_map = {top_resource: top_op}
    bot_op_map = {bot_resource: bot_op}
    mid_ops_map = dict(zip(mid_resources, mid_ops_choices))
    op_map = top_op_map | bot_op_map | mid_ops_map

    return Case(resources, dependencies, resources, dependencies, op_map)


def gen_chain_benchcase(n, principal_op, principal_op_percentage):

    # get a global list of operations
    ops = Operation.diffs_with_leading(principal_op)
    secondary_ops_percentage = (100 - principal_op_percentage) // 3
    weights = [principal_op_percentage/100] + 3*[secondary_ops_percentage/100]
    op_choices = random.choices(ops, k=n, weights=weights)

    # if the result ended with only NOOPs, add a random change operation
    if all([op == Operation.NOOP for op in op_choices]):
        op_choices[0] = random.choice(Operation.diff_change())

    # compute the chain topology
    resources, dependencies = gen_scalable_topology([1]*n, [0]*(n-1))

    # construct the final operations map
    op_map = dict(zip(resources, op_choices))

    return Case(resources, dependencies, resources, dependencies, op_map)


def gen_ranged_benchcases():
    """
    Range all parameters for all topologies,
    returns a list of pairs (case_name, case)
    """

    # global parameters
    ns = [5, 10, 15, 20, 25, 30, 40, 50]
    principal_ops = Operation.diffs()
    principal_op_percentages = [70, 40]

    # parameters per-topologies
    simple_butterfly_top_changes_percentages = [50, 80, 20]
    butterfly_mid_ops = Operation.diffs()
    diamond_top_bot_ops = Operation.diffs()

    cases = []

    # (a) simple 2-stages
    for n in ns:
        for principal_op in principal_ops:
            for principal_op_percentage in principal_op_percentages:
                for top_changes_percentage in simple_butterfly_top_changes_percentages:
                    case_name = f"simple{n}-{principal_op_percentage}p{principal_op}-{top_changes_percentage}{100-top_changes_percentage}"
                    case = gen_simple_benchcase(n, principal_op, principal_op_percentage, top_changes_percentage)
                    cases.append((case_name, case))

    # (b) butterflies
    for n in ns:
        for principal_op in principal_ops:
            for principal_op_percentage in principal_op_percentages:
                for top_changes_percentage in simple_butterfly_top_changes_percentages:
                    for mid_op in butterfly_mid_ops:
                        case_name = f"butterfly{n}-{principal_op_percentage}p{principal_op}-mid{mid_op}-{top_changes_percentage}{100-top_changes_percentage}"
                        case = gen_butterfly_benchcase(n, principal_op, principal_op_percentage, mid_op, top_changes_percentage)
                        cases.append((case_name, case))

    # (c) diamonds
    for n in ns:
        for principal_op in principal_ops:
            for principal_op_percentage in principal_op_percentages:
                for top_op in diamond_top_bot_ops:
                    for bot_op in diamond_top_bot_ops:
                        case_name = f"diamond{n}-{principal_op_percentage}p{principal_op}-top{top_op}-bot{bot_op}"
                        case = gen_diamond_benchcase(n, principal_op, principal_op_percentage, top_op, bot_op)
                        cases.append((case_name, case))

    # (d) chains
    for n in ns:
        for principal_op in principal_ops:
            for principal_op_percentage in principal_op_percentages:
                for i in range(2):
                    case_name = f"chain{n}-{principal_op_percentage}p{principal_op}_{i}"
                    case = gen_chain_benchcase(n, principal_op, principal_op_percentage)
                    cases.append((case_name, case))

    return cases


def run_ranged_benchcases(out_dir):
    cases_with_names = gen_ranged_benchcases()
    case_names, cases = zip(*cases_with_names)

    case_counter = 0
    for case_name, case in cases_with_names:
        case_counter += 1
        print(f"{case_counter} over {len(cases_with_names)} {case_name}")
        run_a_case(case, os.path.join(out_dir, case_name))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        __file__, __doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    cmdparsers = parser.add_subparsers(dest="benchmark", required=True)
    systematic_parser = cmdparsers.add_parser("systematic", help="Generate all possible cases")
    systematic_parser.add_argument("-n", type=int, required=True, help="Number of resources")
    scalable_parser = cmdparsers.add_parser("scalable", help="Generate scalable cases for various topologies")
    parser.add_argument("output_path", nargs=1, help="Path in which output the generated cases")

    args = parser.parse_args()
    debug = False

    match args.benchmark:
        case 'systematic':
            if args.n < 2 or args.n > 4:
                print("Systematic benchmark should be for n=2 to n=4 resources")
                exit(1)
            run_same_systematic_topological_cases(args.output_path[0], args.n)
        case 'scalable':
            run_ranged_benchcases(args.output_path[0])

