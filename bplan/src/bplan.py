#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import subprocess
import json
import time
from datetime import datetime

import utils
import tf2maude
import staged

import logging
logger = logging.getLogger(__name__)
# MAIN_MAUDE = "../semantics/maude/main.maude"

# PLAN = "testdata/govuk-vpc/tfplan_change.json"
# STATE = "testdata/govuk-vpc/tfstate_after_init.json"

def parse(tfplan_path, out_dir=None):

    logger.info(f"Parsing {tfplan_path}...")
    with open(tfplan_path, 'r') as f:
        tfplan = json.load(f)

    # Parse
    target_graph = tf2maude.extract_target_dependencies(tfplan["configuration"]["root_module"].get("resources",[]))
    state_resources = tfplan["prior_state"]["values"]["root_module"].get("resources", []) if "prior_state" in tfplan else []
    state_graph = tf2maude.extract_priorstate_dependencies(state_resources)
    planned_ops = tf2maude.extract_planned_operations(tfplan["resource_changes"])

    # Compute parsed graph layers
    target_stages = staged.split_graph_stages(target_graph)
    target_stages.reverse()
    target_graph_n_per_stages = [ '|'.join(k[-1] for k in stage.keys()) for stage in target_stages ]
    target_graph_n_per_stages_str = '[' + ' -> '.join(target_graph_n_per_stages) + ']'
    state_stages = staged.split_graph_stages(state_graph)
    state_stages.reverse()
    state_graph_n_per_stages = [ '|'.join(k[-6] for k in stage.keys()) for stage in state_stages ]
    state_graph_n_per_stages_str = '[' + ' -> '.join(state_graph_n_per_stages) + ']'

    logger.info(f"""Parsed, # of resources per layers in the Target and State :
{target_graph_n_per_stages_str}
{state_graph_n_per_stages_str}
""")

    if out_dir:
        # output each parsed objects
        out_target_dir = os.path.join(out_dir, "target_graph.mmd")
        with open(out_target_dir, 'w') as f:
            logger.info(f"Writing Target graph into {out_target_dir}")
            f.write(tf2maude.format_mermaid_target(target_graph))
        out_state_dir = os.path.join(out_dir, "state_graph.mmd")
        with open(out_state_dir, 'w') as f:
            logger.info(f"Writing State graph into {out_state_dir}")
            f.write(tf2maude.format_mermaid_state(state_graph))
        out_diff_dir = os.path.join(out_dir, "plan_target_diff.mmd")
        with open(out_diff_dir, 'w') as f:
            logger.info(f"Writing plan diff graph into {out_diff_dir}")
            f.write(tf2maude.format_mermaid_plandiff(target_graph, state_graph, planned_ops))

        # also output maude 'config' that aggregates target, state and operations
        out_config_plan = os.path.join(out_dir, "config_plan.maude")
        config_plan = tf2maude.config_plan(target_graph, state_graph, planned_ops)
        with open(out_config_plan, 'w') as f:
            logger.info(f"Writing Maude plan config into {out_config_plan}")
            f.write(config_plan)

    return target_graph, state_graph, planned_ops


def schedule(target_graph, state_graph, planned_ops, pr, transitive_reduction=False, mmd_out_dir=None):

    logger.info(f"Scheduling...")

    maudeDT = "\n(\n" + tf2maude.format_dependencies_arcs(target_graph,8) + "\n)"
    maudeDS = "\n(\n" + tf2maude.format_dependencies_arcs(state_graph,8) + "\n)"
    maudePlan = "\n(\n" + tf2maude.format_operations(planned_ops,8) + "\n)"
    maudeinput = "select FUNCTIONS .\n"
    maudeinput += f"""
        red mkActionGraphVE({maudeDT}, {maudeDS}, {maudePlan}) .
    """
    action_graphVE_str, stat = utils.call_maude_get_result(maudeinput, pr)

    action_graph = staged.parse_actiongraphVE(action_graphVE_str)
    action_stages = staged.split_graph_stages(action_graph)
    action_graph_n_per_stages = [ len(stage.keys()) for stage in action_stages ]
    action_graph_n_per_stages_str = json.dumps(action_graph_n_per_stages).replace(',', ';')
    logger.info(f"""Action rewrites : duration (seconds) : # of resources per stages
{stat[0]} : {stat[1]/1000} : {action_graph_n_per_stages_str}
""")

    # replace action_graph, stat, etc by the transitive closure
    if transitive_reduction:
        maudeinput = f"""
            red removeTransitiveArcs({action_graphVE_str}) .
        """
        action_graphVE_transitive_str, stat = utils.call_maude_get_result(maudeinput, pr)
        action_graph = staged.parse_actiongraphVE(action_graphVE_transitive_str)
        action_graph_n_per_stages = [ len(stage.keys()) for stage in action_stages ]
        action_graph_n_per_stages_str = json.dumps(action_graph_n_per_stages).replace(',', ';')
        logger.info(f"""Transitive reduction : # of rewrites : duration (s) : # of resources per stages
{stat[0]} : {stat[1]/1000} : {action_graph_n_per_stages_str}
""")

    if mmd_out_dir:
        out_action_graph = os.path.join(mmd_out_dir, "action_graph.mmd")
        with open(out_action_graph, 'w') as f:
            logger.info(f"Writing Action graph schedule into {out_action_graph}")
            f.write(tf2maude.format_mermaid_actions(action_graph))

        # also output maude 'config' that aggregates target, state and action graph
        out_config_exec = os.path.join(mmd_out_dir, "config_exec.maude")
        config_exec = tf2maude.config_exec(target_graph, state_graph, action_graph)
        with open(out_config_exec, 'w') as f:
            logger.info(f"Writing Maude exec config into {out_config_exec}")
            f.write(config_exec)

    return action_graph


def main():
    parser = argparse.ArgumentParser(
        __file__, __doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--outdir", help="Output directory, default is bplans/ at the location of the plan.json")
    cmdparsers = parser.add_subparsers(dest="command", required=True)
    parser.add_argument("directory", nargs=1, help="Directory containing the input plan.json")

    parser_parse = cmdparsers.add_parser("parse", help="parse a plan.json into a Target graph, a State graph and a Plan")
    parser_schedule = cmdparsers.add_parser("schedule", help="schedules the order of actions")
    parser_schedule.add_argument("--reduce", action="store_true", help="Compute the transitive reduction of the action graph")
    parser_check = cmdparsers.add_parser("check", help="check for instabilities")

    checkparsers = parser_check.add_subparsers(dest="which_check", required=True)
    checksubparsers = [
        checkparsers.add_parser("stable", help="model-check(stable) once for the whole execution"),
        checkparsers.add_parser("stable-deps", help="model-check(stable(r1,r2)) for all dependencies (r1,r2) in state"),
        # stable_parser.add_argument("--details", action="store_true", help="model-check(stable(r1,r2)) for all risky deps. Not implemented.")
        checkparsers.add_parser("not-unstable", help="model-check(stable \\/ estable), if true, the config is not unstable")
    ]
    for checksubparser in checksubparsers:
        checksubparser.add_argument("which_predicate", choices=["dep", "res"])
    # parser_check.add_argument("--timeout", type=int, help="Seconds to wait the model-checker before running the static check")
    # parser_check.add_argument("--details", action="store_true", help="Run the model-checker on every risky dependency arc")

    # print(parser.parse_args())
    # exit(1)
    args = parser.parse_args()
    arg_dir = args.directory[0]
    debug = args.debug

    # JSON Terraform plan can be args.command
    # or we look into the args.command directory for a *plan*.json, read the one with the shortest filename.
    tfplan_path = utils.find_tfplan(arg_dir)
    if not tfplan_path:
        print(f"No plan found at {arg_dir}, exiting.")
        exit(1)

    # Create the output directory in which write result files
    out_path = os.path.join(os.path.dirname(tfplan_path), "bplans") if args.outdir == None else args.outdir
    os.makedirs(out_path, exist_ok=True)

    plan_name = os.path.splitext(os.path.basename(tfplan_path))[0]
    log_filename = os.path.join(out_path, \
                                f"log-{args.command}" + \
                                (f"-{args.which_check}" if hasattr(args, "which_check") else "") + \
                                datetime.now().strftime("-%b%d") + \
                                ".txt")
                                # f"-{plan_name}" + \

    logging.basicConfig(
        filename=log_filename,
        filemode='w', # override
        level=logging.INFO,
        format='%(message)s'
    )

    # reconstruct a printable argument list
    args_strs = []
    for aname, avalue in vars(args).items():
        if avalue is not None:
            if isinstance(avalue, bool) and avalue:
                args_strs.append("--"+aname)
            elif isinstance(avalue, str):
                args_strs.append(avalue)

    print(f"Running BPlan '{' '.join(args_strs)}' on plan {tfplan_path}")
    print(f"  Output path: {out_path}")
    print(f"  Log file: {log_filename} ")
    match args.command:

        case "parse":
            parse(tfplan_path, out_path)

        case "schedule":
            target_graph, state_graph, planned_ops = parse(tfplan_path, out_path)
            with utils.new_maude_subprocess() as pr:
                schedule(target_graph, state_graph, planned_ops, pr, mmd_out_dir=out_path, transitive_reduction=args.reduce)

        case "check":
            match args.which_check:

                case "stable":
                    target_graph, state_graph, planned_ops = parse(tfplan_path, out_path)
                    with utils.new_maude_subprocess() as pr:
                        action_graph = schedule(target_graph, state_graph, planned_ops, pr, mmd_out_dir=out_path)
                        config = tf2maude.config_exec(target_graph, state_graph, action_graph)
                        start = time.time()
                        bool_ret = staged.model_check_full(config, f"stable-{args.which_predicate}", pr)
                        end = time.time()
                        logger.info(f"Check-stable using m-c done, bool_result / time:\n{bool_ret} : {end - start}")

                case "stable-deps":
                    target_graph, state_graph, planned_ops = parse(tfplan_path, out_path)
                    with utils.new_maude_subprocess() as pr:
                        action_graph = schedule(target_graph, state_graph, planned_ops, pr, mmd_out_dir=out_path)
                        config = tf2maude.config_exec(target_graph, state_graph, action_graph)
                        state_deps = ((r_inst[3:-5], nbh_inst[3:-5]) for r_inst, nbh_insts in state_graph.items() for nbh_inst in nbh_insts)
                        estable_deps = set()
                        start = time.time()
                        deleted_res = [ act[1] for (act, nbh) in action_graph.items() ]
                        risky_deps = [ (rcodep, rdel) for rdel in deleted_res for rcodep in staged.get_codeps(rdel, state_graph) ]
                        for r1, r2 in risky_deps:
                            bool_ret = staged.model_check_full(config, f"stable({r1}, {r2})", pr)
                            if bool_ret == False:
                                estable_deps.add((r1, r2))
                        end = time.time()
                        logger.info(f"estable-deps: {estable_deps}")
                        logger.info(f"Check-stable-deps using m-c done, #non-stables / time:\n{len(estable_deps)} : {end - start}")

                case "not-unstable":
                    target_graph, state_graph, planned_ops = parse(tfplan_path, out_path)
                    with utils.new_maude_subprocess() as pr:
                        action_graph = schedule(target_graph, state_graph, planned_ops, pr, mmd_out_dir=out_path)
                        start = time.time()
                        config = tf2maude.config_exec(target_graph, state_graph, action_graph)
                        bool_ret = staged.model_check_full(config, "stable \\/ estable", pr)
                        end = time.time()
                        logger.info(f"Check-not-unstable using m-c(stable \\/ estable) done, bool_result / time:\n{bool_ret} : {end - start}")

if __name__ == "__main__":
    main()

