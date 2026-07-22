
import bplan
import tf2maude
import utils


def get_codeps(resname, state_graph):
    """
    returns all codependencies of resname
    """
    codeps = []
    for r, ds in state_graph.items():
        for d in ds:
            if d.find(resname) > 0:
                codep = r[3:r.find(',')]    # transform "ri(codep, old)" into "codep"
                codeps.append(codep)
    return codeps


def parse_actiongraphVE(agraph: str) -> dict:
    """
    returns a map from action pairs (prim_act, res) to sets of neighbor actions (prim_act, res)
    """

    if agraph.find("graphVE(eps") >= 0:
        return dict()

    action_graph = {}
    ress_beg = agraph.index("graphVE(")+8
    ress_end = agraph.index("),", ress_beg)
    deps_beg = ress_end + 2
    # deps_end = agraph.rindex("))")

    # print("RES:", agraph[ress_beg:ress_end].split("a("))
    # print("DEPS:", agraph[deps_beg:deps_end])

    ress_str = agraph[ress_beg:ress_end]
    for astr in ress_str.split("a(")[1:]:
        prim_act, res = astr.split(",")
        # res = res.strip().lstrip("'").rstrip(")")
        res = res.strip().rstrip(")")
        action_graph[(prim_act, res)] = set()

    deps = agraph[deps_beg:].strip()
    if deps.startswith("("):
        deps = deps[1:deps.rindex(")")]
    if not deps.startswith("eps"):
        while deps:
            a1_beg = deps.index("a(")+2
            a1_end = deps.index("->", a1_beg)
            a2_beg = deps.index("a(", a1_end)+2
            a2_end = deps.index(")", a2_beg)+1
            a1 = deps[a1_beg:a1_end].replace(' ','').replace('\n','').strip()
            a2 = deps[a2_beg:a2_end].replace(' ','').replace('\n','').strip()
            prim_act1, res1 = a1.split(",")
            # res1 = res1.strip().lstrip("'").rstrip(")")
            res1 = res1.strip().rstrip(")")
            prim_act2, res2 = a2.split(",")
            # res2 = res2.strip().lstrip("'").rstrip(")")
            res2 = res2.strip().rstrip(")")
            action_graph[(prim_act1, res1)].add((prim_act2, res2))
            deps = deps[a2_end+1:].strip()

    return action_graph


def model_check_full(config, prop, pr):
    """
    with Maude pr subprocess, run modelCheck on config and prop
    returns true if the property is verified, false otherwise
    """
    maudeinput = "select MUTABLE-TF-PLM-PROPS .\n"
    maudeinput += f"reduce modelCheck({config},\n{prop}) .\n"
    pr.stdin.write(maudeinput)
    pr.stdin.flush()
    for line in pr.stdout:
        s = "result "
        if line.startswith("result "):
            line = line[len(s):]
            break
    if line.startswith("Bool: true"):
        return True
    elif line.startswith("ModelCheckResult: counterexample("):
        # read until 'deadlock' to empty the buffer
        for line in pr.stdout:
            if line.find("deadlock") > 0:
                break
        return False
    raise Exception("ModelCheck didn't work properly")

def split_graph_stages(graph):
    """
    Returns the list of stage graphs (only nodes without arcs), from sinks to sources
    Nodes of the top stages corresponds to sinks, i.e. thoses without any neighbors (or with neighbors not in the original graph)
    Top nodes are added as stage nodes and then removed from the original graph copy.
    The operation repeats until no node exists.
    """
    stages = []
    all_nodes = set(graph.keys())
    graph_items_tmp = dict(graph)
    while graph_items_tmp:
        top_graph, below_graph = dict(), dict()
        for node, nbhs in graph_items_tmp.items():
            if not nbhs or not set(nbhs).issubset(all_nodes):
                top_graph[node] = []
            else:
                below_graph[node] = nbhs
        graph_items_tmp = dict()
        for node, nbhs in below_graph.items():
            graph_items_tmp[node] = set(nbhs).difference(set(top_graph.keys()))
        stages.append(dict(top_graph))
    return stages


