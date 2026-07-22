
import json
import re

skipped_resname_prefixes = ("data", "local", "var", "each", "count")

def get_references_deep(es):
    """ From an "expression", find deep "references" objects """
    if isinstance(es, dict):
        maybe_refs = es.get("references")
        if maybe_refs:
            return [ maybe_refs ]
        else:
            return [ refs for kes in es.values() for refs in get_references_deep(kes) ]
    elif isinstance(es, list):
        return [ refs for kes in es for refs in get_references_deep(kes) ]
    else:
        return []


def get_resname(address):
    """
        From an "address", get the resource name.
        Keep nested modules instance id ; remove resource instance id and key reference if it exists
        return the resource name or None in case of a data
    """
    if address.startswith(skipped_resname_prefixes):
        return None
    if address.startswith("module"):
        a = address.split('.',2)
        if len(a) < 3:
            return None # probably a reference to a module's output
        modulename = '.'.join(a[0:2])
        resname = get_resname(a[2])
        if resname:
            return f"{modulename}.{resname}"
    else:
        return '.'.join(address.split('[')[0].split('.',2)[:2])


def extract_planned_operations(resource_changes):
    """
        For the list of `resource_changes` comming from `terraform plan`,
        look for the `change.actions` list and
        returns the planned operations as a dict from resname to list of actions
        /!\ all indexed resources (count/foreach) are filtered, only the last one is kept
    """
    # put resources in a dict, keyed by the address without the index, valued by the change action list
    # indexed resources are thus filtered, only the last one is kept
    uniq_resource_changes = {}
    for res in resource_changes:
        resname = get_resname(res["address"])
        if not resname:
            continue
        previous_res = uniq_resource_changes.get(resname)
        if not previous_res:
            uniq_resource_changes[resname] = res["change"]["actions"]
        else:
            print(f"Discarding planned operations of duplicate {resname}: {res['address']}")
    return { f"'{r}": ops for r, ops in uniq_resource_changes.items() }


def extract_target_dependencies(resources):
    """
        For the list of resources, look for `depends_on` and `expressions.*.references`
        returns the dependencies as a dict (resname, set of dependencies)
        /!\ for_each resources are counted as one resource,
            a reference to a for_each resource is counted as a dependency to the group

        'resources' : usually come from a tfplan.json, key `configuration.root_module.resources`
    """
    # extract from the TF JSON
    deps = {}
    for res in resources:
        resname = get_resname(res["address"])
        if resname:
            deps[resname] = set()
            for dep in res.get("depends_on", []):
                depname = get_resname(dep)
                if depname:
                    deps[resname].add(depname)
            for k, es in res.get("expressions", {}).items():
                # when the rhs is an object, explore until we find all objects "references"
                for refs in get_references_deep(es):
                    for ref in refs:
                        # check if it's a prefix of an already found ref
                        if 0 == len([ d for d in deps[resname] if d.startswith(ref)] ):
                            depname = get_resname(ref)
                            if depname:
                                deps[resname].add(depname)
    # else, format in Maude: add leading quotes and ri(,old) for states
    target_deps = {}
    for r, ds in deps.items():
        target_deps[f"'{r}"] = [ f"'{d}" for d in ds ]
    return target_deps

def extract_priorstate_dependencies(resources):
    """
        For all 'resources'
        look for the first instance and its field 'dependencies',
        returns all the dependencies as a dict (resname, set of dependencies)
    """
    # extract from the terraform.tfstate JSON
    deps = {}
    for res in resources:
        resname = f"{res['type']}.{res['name']}"
        deps[resname] = set(res.get("depends_on", []))  # may crash if multiple instances, we should report a better error
    # format in Maude: add leading quotes and ri(,old)
    state_graph = {}
    for r, ds in deps.items():
        state_graph[f"ri('{r},old)"] = [ f"ri('{d},old)" for d in ds]
    return state_graph


def format_resources_set(ress, indent=0):
    if len(ress) == 0:
        return ' '*indent + "eps"
    else:
        return '\n'.join(' '*indent + res for res in ress)

def format_dependencies_adjlist(deps, indent=0):
    if len(deps) == 0:
        return ' '*indent + "eps"
    fdepss = [] # list of strings combining all deps for each node
    for r, ds in deps.items():
        nbhs = "eps" if not ds else ' '.join(f"{d}" for d in ds)
        fdepss.append(f"{r} -> neighbors({nbhs})")
    return '\n'.join(' '*indent + fdeps for fdeps in fdepss)

def format_dependencies_arcs(deps, indent=0):
    fdeps = '\n'.join(' '*indent + f"{r} -> {d}" for r, ds in deps.items() for d in ds)
    return fdeps if fdeps else (' '*indent + "eps")

def format_operations(ops, indent=0):
    """ maude format """
    return '\n'.join(' '*indent + f"{r} -> po({' ; '.join(acts).upper()})" for r, acts in ops.items())

def format_target_names(target_graph):
    """ returns the same graph but cut leading quotes of names """
    target_graph_norm = {}
    for r1, ds in target_graph.items():
        target_graph_norm[r1[1:]] = [ r2[1:] for r2 in ds ]
    return target_graph_norm

def format_state_names(state_graph):
    """ returns the same graph but cut ri('resname,old) of names """
    state_graph_norm = {}
    for r1, ds in state_graph.items():
        state_graph_norm[r1[4:-5]] = [ r2[4:-5] for r2 in ds ]
    return state_graph_norm

def format_po_names(planned_ops):
    """ returns the same dict but cut resname of keys """
    planned_ops_norm = {}
    for r1, ops in planned_ops.items():
        planned_ops_norm[r1[1:]] = ops
    return planned_ops_norm

def mermaid_config(title = None):
    ret = "---\n"
    if title:
        ret += f"title: {title}\n"
    ret += """config:
flowchart:
    defaultRenderer: elk
---
"""
    return ret

def format_mermaid_target(target_graph, indent=0):
    ret = mermaid_config("Target state")
    ret += "flowchart BT\n"
    target_graph_norm = format_target_names(target_graph)
    for r in target_graph_norm.keys():
        ret += f"{r}\n"
    for r1, ds in target_graph_norm.items():
        for r2 in ds:
            ret += f"{r1} --> {r2}\n"
    return ret

def format_mermaid_state(state_graph, indent=0):
    ret = mermaid_config("Current state")
    ret += "flowchart BT\n"
    state_graph_norm = format_state_names(state_graph)
    for r in state_graph_norm.keys():
        ret += f"{r}\n"
    for r1, ds in state_graph_norm.items():
        for r2 in ds:
            ret += f"{r1} --> {r2}\n"
    return ret

def format_mermaid_actions(action_graph):
    ret = mermaid_config("Actions")
    ret += "flowchart TB\n" + \
        "classDef NO-OP  fill:#F5F5F5;\n" + \
        "classDef CREATE fill:#D5E8D4;\n" + \
        "classDef UPDATE fill:#FFF2CC;\n" + \
        "classDef DELETE fill:#FF9999;\n"
    ret += "%% Nodes\n"
    for prim_act, res in action_graph.keys():
        ret += f"{prim_act}-{res}({res}):::{prim_act};\n"
    ret += "%% Arcs\n"
    for (prim_act1, res1), ds in action_graph.items():
        if ds:
            ret += " & ".join(f"{prim_act2}-{res2}({res2})" for prim_act2, res2 in ds)
            ret += f" --> {prim_act1}-{res1};\n"
    return ret

def format_mermaid_plandiff(target_graph, state_graph, planned_ops):
    ret = mermaid_config("Plan diff")
    ret += "flowchart BT\n" + \
        "classDef no-op  fill:#F5F5F5\n" + \
        "classDef create fill:#D5E8D4,stroke-width:2px,stroke-dasharray:5 5\n" + \
        "classDef delete fill:#FF9999,stroke-width:2px,stroke-dasharray:5 5\n" + \
        "classDef update fill:#FFF2CC\n" + \
        "classDef replace fill:#FF9999\n"

    target_graph_norm = format_target_names(target_graph)
    state_graph_norm = format_state_names(state_graph)

    ret += "%% Nodes\n"
    for r, ops in format_po_names(planned_ops).items():
        if 1 == len(ops):
            ret += f"{r}:::{ops[0]}\n"
        else:
            if ops[0][0] == 'c':
                ret += f"{r}:::replace@{{ shape: trap-t }}\n"
            else:
                ret += f"{r}:::replace@{{ shape: trap-b }}\n"

    # diff arcs
    # With `prior_state` from plan.json as the state_graph, target dependencies are included
    # so check only state deps that are not in target, and not the reverse
    deletes, noops = set(), set()
    for r1, ds in state_graph_norm.items():
        for r2 in ds:
            if r2 not in target_graph_norm.get(r1, []):
                deletes.add((r1,r2))
            else:
                noops.add((r1,r2))

    ret += "%% Arcs\n"
    for r1, r2 in deletes:
        ret += f"{r1} -.-> {r2}\n"
    for r1, r2 in noops:
        ret += f"{r1} --> {r2}\n"
    return ret


def format_action_graph(action_graph, indent=0):
    """
    From a map of pairs (a, r) to lists of pairs,
    returns the string representing the action graph in maude as adjacency list
    """
    adj = []
    for (a1, r1), nbhs in action_graph.items():
        node = f"a({a1}, {r1})"
        neighbors = [ f"a({a2}, {r2})" for a2, r2 in nbhs ]
        if not neighbors:
            neighbors = ["eps"]
        adj.append((node, "neighbors(" + ' '.join(neighbors) + ")"))
    if not adj:
        return "graphAdj(eps)"
    return ' '*indent + \
        "graphAdj(\n" + \
            '\n'.join([' '*(indent+4) + f"{node} -> {neighbors}" for node, neighbors in adj]) + \
        '\n' + ' '*indent + ')'

## Other functions not primarilly used by BPlan

def config_plan(target_deps, state_deps, planned_ops) -> str:
    ind = 16
    return f"""newConfig(
        target(
            resources: (
{format_resources_set(target_deps.keys(), ind)}
            ),
            dependencies: (
{format_dependencies_arcs(target_deps, ind)}
            )
        ),
        state(
            resources: (
{format_resources_set(state_deps.keys(), ind)}
            ),
            dependencies: (
{format_dependencies_arcs(state_deps, ind)}
            )
        ),
        (
{format_operations(planned_ops, ind-4)}
        )
    )
"""

def config_exec(target_deps, state_deps, action_graph) -> str:
    ind = 16
    return f"""newExec(
        target(
            resources: (
{format_resources_set(target_deps.keys(), ind)}
            ),
            dependencies: (
{format_dependencies_arcs(target_deps, ind)}
            )
        ),
        state(
            resources: (
{format_resources_set(state_deps.keys(), ind)}
            ),
            dependencies: (
{format_dependencies_arcs(state_deps, ind)}
            )
        ),
        (
{format_action_graph(action_graph, ind-4)}
        )
    )
"""

def format_trace_to_maude(trace):
    """
    takes a list of 3-tuples, e.g. (start, CREATE, r)
    and returns their join as start(a(CREATE,'r))
    """
    return ' '.join(f"{e[0]}(a({e[1]},'{e[2]}))" for e in trace)

def format_tfoutput_apply_trace(file):
    trace = []
    addr_regex = "[a-z][a-z_0-9]*\.[a-zA-Z_0-9]*(\[\"[^\"]*\"\])?"    # type.name["inst"]
    start_action_pattern = re.compile(f"^{addr_regex}( \(deposed [^\)]*\))?: ")
    for line in file:
        m = start_action_pattern.match(line)
        if m:
            r = m.group()[:-2].split(' ')[0].split('[')[0]
            sline = line[m.span()[1]:]

            if sline.startswith("Creating..."):
                trace.append(("start", "CREATE", f"{r}"))
            elif sline.startswith("Creation complete"):
                trace.append(("end", "CREATE", f"{r}"))

            elif sline.startswith("Modifying..."):
                trace.append(("start", "UPDATE", f"{r}"))
            elif sline.startswith("Modifications complete"):
                trace.append(("end", "UPDATE", f"{r}"))

            elif sline.startswith("Destroying..."):
                trace.append(("start", "DELETE", f"{r}"))
            elif sline.startswith("Destruction complete"):
                trace.append(("end", "DELETE", f"{r}"))

            elif sline.startswith("Refreshing state..."):
                pass
            elif sline.startswith("Still"):
                pass
            else:
                raise Exception("Cannot deduce trace event in line", line)

    return trace
