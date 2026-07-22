#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json

import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import bplan
import utils
import tf2maude


def next_actions(action, action_graph):
    """
    returns all "codependencies" of the action in the action graph
    it corresponds to those executed "after"
    """
    preds = set()
    for a1, nbhs in action_graph.items():
        for a2 in nbhs:
            if a2 == action:
                preds.add(a1)
    return preds


def validate_trace_against_agraph(subdir, pr, debug=False):

    tfplan_path = utils.find_tfplan(subdir)
    if not tfplan_path:
        return 2 # skip

    tftrace_path = os.path.join(subdir, "trace.txt")
    if not os.path.isfile(tftrace_path):
        print(f"Missing {tftrace_path}, skipping")
        return 2    # skip
    with open(tftrace_path, 'r') as f:
        tftrace = tf2maude.format_tfoutput_apply_trace(f)
    assert tftrace, f"Could not parse trace in {tftrace_path}"

    # BPlan parse and schedule
    target_graph, state_graph, planned_ops = bplan.parse(tfplan_path, out_dir=None)
    action_graph = bplan.schedule(target_graph, state_graph, planned_ops, pr, transitive_reduction=False)

    # prepare the set of next actions (reverse the action graph)
    next_actions = { act: set() for act in action_graph.keys() }
    for a1, nbhs in action_graph.items():
        for a2 in nbhs:
            next_actions[a2].add(a1)

    # sets of pairs (ACTION, 'resname)
    running = set()
    completed = set()
    available = set([ act for act, nbhs in action_graph.items() if not nbhs ])

    if debug:
        print("TF TRACE", tftrace)
        print("ACTION GRAPH", [ f"{act}: {nbhs}" for act, nbhs in action_graph.items() ])
        print("INIT AVAILABLE", available)

    for te in tftrace:
        evt, action, resname = te
        act = (action, "'"+resname) # add quote (Maude format)
        if evt == "start":
            if act in available:
                available.remove(act)
                running.add(act)
            else:
                print(te, "but not available", act, act in available)
        elif evt == "end":
            if act in running:
                running.remove(act)
                completed.add(act)
                for act_succ in next_actions[act]:
                    act_succ_preds = action_graph[act_succ]
                    if act_succ_preds.issubset(completed):
                        available.add(act_succ)
            else:
                print(te, "but not running")
        else:
            print("Trace event neither 'start' nor 'end'")
            return 3
        if debug:
            print("AFTER", te)
            print("  RUNNING", running)
            print("  COMPLET", completed)
            print("  AVAILAB", available)

    if not running and not available and completed == set(action_graph.keys()):
        return 0 # OK
    else:
        return 1 # KO

def validate_trace_search(subdir, pr, debug=False):
    """
    For a Case in "subdir", run a `search` of the Trace on the config built from Plan and State
    Returns codes: O=OK, 1=KO, 2=Skipped
    """

    tfplan_path = utils.find_tfplan(subdir)
    if not tfplan_path:
        return 2 # skip
    if tfplan_path == subdir:
        subdir = "."

    target_graph, state_graph, planned_ops = bplan.parse(tfplan_path, out_dir=None)

    config = tf2maude.config_plan(target_graph, state_graph, planned_ops)
    if debug:
        print(config)

    tftrace_path = os.path.join(subdir, "trace.txt")
    if not os.path.isfile(tftrace_path):
        print(f"Missing {tftrace_path}, skipping")
        return 2    # skip
    with open(tftrace_path, 'r') as f:
        tftrace = tf2maude.format_tfoutput_apply_trace(f)
    assert tftrace, f"Could not parse trace in {tftrace_path}"

    trace_config = f"""
    <
        target: Target,
        planned: Plan,
        actions: graphAdj(eps),
        state: State,
        ongoing: eps,
        phase: done,
        trace: {tf2maude.format_trace_to_maude(tftrace)}
    >"""

    maudeinput = "select RULES .\n"
    maudeinput += f"search [1] {config} =>* {trace_config} .\n"
    if debug:
        print(maudeinput)
    pr.stdin.write(maudeinput)
    pr.stdin.flush()
    for line in pr.stdout:
        if line.startswith("=========="):
            break
    for line in pr.stdout:
        if line.startswith("No solution."):
            return 1    # Ko
        elif line.startswith("Solution 1"):
            return 0    # Ok
    return 3    # error


def validate_all_cases(subdirs, validate_func, debug=False):
    rets = [ [], [], [], [] ]
    progress_step = 10
    progress = 0
    pr = utils.new_maude_subprocess()
    for subdir in subdirs:
        progress += 1
        print(f"validating {subdir} ({progress})", flush=True)
        # if progress % progress_step == 0:
        #     print(f"progress: {progress}")
        ret = validate_func(subdir, pr, debug=debug)
        if ret == 3:
            pr.terminate()
            pr = utils.new_maude_subprocess()
        rets[ret].append(os.path.basename(subdir))
        # print(f"{ret} {subdir.path}")

    print(f"Total: {len(rets[0])} OKs, {len(rets[1])} KOs, {len(rets[2])} Skipped, {len(rets[3])} Errorred.")
    print("KOs", rets[1])
    print("Skips", rets[2])
    print("Errors", rets[3])


if __name__ == "__main__":

    # If more than one directory is provided, validate on each of them, otherwise validate on all subdirectories of the provided directory
    commands = [ "actiongraph", "execrules" ]
    if len(sys.argv) < 2 or not sys.argv[1] in commands:
        print(f"Usage: python3 {sys.argv[0]} <actiongraph|execrules> <plan.json|directory>")
        exit(1)

    arg_cmd = sys.argv[1]
    debug = False

    validate_ret = {
        0: "OK",
        1: "KO",
        2: "Skipped",
        3: "Errorred"
    }

    match arg_cmd:
        case "actiongraph":
            validation_func = validate_trace_against_agraph

        case "execrules":
            validation_func = validate_trace_search

    pr = utils.new_maude_subprocess()
    # with utils.new_maude_subprocess() as pr:
    if len(sys.argv) > 3:
        validate_all_cases(sys.argv[2:], validation_func, debug)
    else:
        path = sys.argv[2]
        if os.path.isfile(path) and path.endswith('.json'):
            validate_all_cases([path], validation_func, debug)
        else:
            subdir_paths = [ subdir.path for subdir in os.scandir(path) ]
            validate_all_cases(subdir_paths, validation_func, debug)

