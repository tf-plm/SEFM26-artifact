#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import glob
import re
import statistics
import json

"""
Case parameters and execution results parsed variables
"""

TOPOLOGY                = "Topology"
N                       = "Number of resources"
PRINCIPAL_OP            = "Principal op"
PRINCIPAL_OP_PERCENTAGE = "Principal op percentage"

MID_OP = "Mid op"

TOP_OP = "Top op"
BOT_OP = "Bot op"

TOP_CHANGES_PERCENTAGE = "Top changes percentage"
BOT_CHANGES_PERCENTAGE = "Bot changes percentage"

SYNTH_ID = "id"
A_CHANGE = "A change op"
B_CHANGE = "B change op"
C_CHANGE = "C change op"
D_CHANGE = "D change op"

PATH = "Path"

PARSE_STAGES_TARGET = "Target graph layers"
PARSE_STAGES_STATE  = "State graph layers"

SCHEDULE_DURATION          = "Schedule duration"
SCHEDULE_REWRITES          = "Schedule #Rewrites"
SCHEDULE_TRANSRED_DURATION = "Schedule trans. red. duration"
SCHEDULE_STAGES            = "Schedule stages"

CHECK_DURATION = "Staged Check duration"
N_ESTABLES     = "Staged #Estables"
N_RISKY_CHECKS = "Staged #Risky_dep checks"
N_CHECKS       = "Staged #Checks"

FULL_CHECK_DURATION = "Full Check ESTABLE duration"
FULL_CHECK_RESULT   = "Full Check ESTABLE result"

STATIC_CHECK_DURATION = "Check Static duration"
STATIC_N_ESTABLES     = "Check Static #Estables"

CHECK_STABLE_GLOBAL_DURATION = "Check global STABLE duration"
CHECK_STABLE_GLOBAL_RESULT   = "Check global STABLE result"

CHECK_STABLE_DEPS_DURATION = "Check deps STABLE duration"
CHECK_STABLE_DEPS_RESULT   = "Check deps STABLE result"

CHECK_NOT_UNSTABLE_DURATION = "Check NOT UNSTABLE duration"
CHECK_NOT_UNSTABLE_RESULT   = "Check NOT UNSTABLE result"

"""
The header of output data, in order
"""
HEADER = [

    #
    # case parameters in the name
    #

    # PATH,

#     # cases4_same
    SYNTH_ID,
    A_CHANGE,
    B_CHANGE,
    C_CHANGE,
    D_CHANGE,

    # # bench_cases
    # TOPOLOGY, N, 
    # PRINCIPAL_OP, PRINCIPAL_OP_PERCENTAGE,
    # TOP_CHANGES_PERCENTAGE,
    # MID_OP,
    # TOP_OP, BOT_OP,

    #
    # case execution results, based on BPLan argument
    #

    # parse
    PARSE_STAGES_TARGET,
    PARSE_STAGES_STATE,

    SCHEDULE_STAGES,

    # schedule
    # SCHEDULE_REWRITES,
    SCHEDULE_DURATION,
    SCHEDULE_TRANSRED_DURATION,

    # check not unstable
    CHECK_NOT_UNSTABLE_RESULT,
    CHECK_NOT_UNSTABLE_DURATION,

    # check-full-stable
    CHECK_STABLE_GLOBAL_RESULT,
    CHECK_STABLE_GLOBAL_DURATION,

    CHECK_STABLE_DEPS_RESULT,
    CHECK_STABLE_DEPS_DURATION,

    # # check-staged
    # CHECK_DURATION,
    # N_ESTABLES,
    # N_RISKY_CHECKS,
    # N_CHECKS,

    # check-static
    STATIC_N_ESTABLES,
    STATIC_CHECK_DURATION,

]


ops_regex = "CREATE|DELETE|NOOP|UPDATE|CREATE_DELETE|DELETE_CREATE"
CASE_NAME_SCALABLE_REGEX = fr"""
    ^.*
    (?P<TOPOLOGY>bipartite|butterfly|diamond|chain)
    (?P<N>\d+)-
    (?P<PRINCIPAL_OP_PERCENTAGE>\d+)p(?P<PRINCIPAL_OP>{ops_regex})
    (
        -mid(?P<MID_OP>{ops_regex})                                 # only for butterfly
        | -top(?P<TOP_OP>{ops_regex})-bot(?P<BOT_OP>{ops_regex})    # only for diamond
    )?
    (-(?P<TOP_CHANGES_PERCENTAGE>\d\d)\d\d)?                        # only for bipartite and butterfly
    (_(?P<SYNTH_ID>\d+))?                                           # optional id (only for chains ATM). FIXME, rename with -
    $
"""
# e.g. `bipartite5-70pNOOP-8020`

CASE_NAME_SYSTEMATIC_REGEX = fr"""
    ^.*
    A_(?P<A_CHANGE>{ops_regex})
    -B_(?P<B_CHANGE>{ops_regex})
    (-C_(?P<C_CHANGE>{ops_regex}))?
    (-D_(?P<D_CHANGE>{ops_regex}))?
    -(?P<SYNTH_ID>\d+)$
"""

LOG_FILE_GLOB = r"log-*.txt"
LOG_FILE_REGEX = r"^.*log-(?P<which_log>[-\w]+)-[^-]*.txt$"

def read_data_from_result_stdouts(bench_paths, case_name_regex):
    """
    In all bench_paths, read file '{bench_paths}/{log_filename}',
    extract case parameters from the path and execution result variables from the content of the log,
    Returns the list of dicts containing interpreted values of case parameters and extracted durations
    """

    case_name_pattern = re.compile(case_name_regex, re.VERBOSE)
    log_file_pattern = re.compile(LOG_FILE_REGEX, re.VERBOSE)

    # explore all paths
    cases_records = []
    for bench_path in bench_paths:
        print(bench_path)

        # Match the input path with the regex for parameters and
        # Initialize the record for this case, use the value of case parameters as keys
        case_name_matching = case_name_pattern.match(bench_path).groupdict()
        case_rec = { globals()[k]: v for k, v in case_name_matching.items() }
        # case_rec = { PATH: log }

        # all found log files
        logfiles = glob.glob(os.path.join(bench_path, "bplans", LOG_FILE_GLOB))

        for benchlog_filename in logfiles:
            log_file_matching = log_file_pattern.match(benchlog_filename)
            which_log = log_file_matching.group(1)

            try:
                with open(benchlog_filename, 'r') as f:

                    for line in f:
                        if line.lstrip().startswith("Parsed"):
                            line = f.readline()
                            case_rec[PARSE_STAGES_TARGET] = line.strip()
                            line = f.readline()
                            case_rec[PARSE_STAGES_STATE] = line.strip()
                            break

                    for line in f:
                        if line.lstrip().startswith("Action"):
                            stat = f.readline().split(':')
                            case_rec[SCHEDULE_REWRITES] = int(stat[0])
                            case_rec[SCHEDULE_DURATION] = float(stat[1])
                            case_rec[SCHEDULE_STAGES] = stat[2].strip()
                            break
                    match which_log:

                        case "schedule":
                            for line in f:
                                if line.lstrip().startswith("Transitive"):
                                    stat = f.readline().split(':')
                                    case_rec[SCHEDULE_TRANSRED_DURATION] = float(stat[1])
                                    break

                        case "check-static":
                            for line in f:
                                if line.lstrip().startswith("Check-static"):
                                    stat = line.split(':')
                                    case_rec[STATIC_CHECK_DURATION] = float(stat[1])
                                    estables_str = f.readline()
                                    assert estables_str.startswith("estables:"), f"Cannot find estables log: {estables_str}"
                                    case_rec[STATIC_N_ESTABLES] = int(estables_str.split(':')[1])
                                    break

                        case "check-stable":
                            for line in f:
                                if line.lstrip().startswith("Check-stable"):
                                    stat = f.readline().split(':')
                                    case_rec[CHECK_STABLE_GLOBAL_RESULT] = {'True': True, 'False': False}[stat[0].strip()]
                                    case_rec[CHECK_STABLE_GLOBAL_DURATION] = float(stat[1])
                                    break

                        case "check-stable-deps":
                            for line in f:
                                if line.lstrip().startswith("Check-stable-deps"):
                                    stat = f.readline().split(':')
                                    case_rec[CHECK_STABLE_DEPS_RESULT] = int(stat[0])
                                    case_rec[CHECK_STABLE_DEPS_DURATION] = float(stat[1])
                                    break

                        case "check-not-unstable":
                            for line in f:
                                if line.lstrip().startswith("Check-not-unstable"):
                                    stat = f.readline().split(':')
                                    case_rec[CHECK_NOT_UNSTABLE_RESULT] = {'True': True, 'False': False}[stat[0].strip()]
                                    case_rec[CHECK_NOT_UNSTABLE_DURATION] = float(stat[1])
                                    break

                        case _:
                            print("CHECK NOT RECOGNIZED", which_log)

            except FileNotFoundError as e:
                print(f"Skipping file-not-found {benchlog_filename}")
                continue

        cases_records.append(case_rec)


    return cases_records

def format_stat_record(stat_record):
    ret = {}
    for k, v in stat_record.items():
        if None == v:
            ret[k] = ""
        elif k.lower().find("percentage") > 0:
            v = int(v)
            if v > 1 and v <= 100:
                ret[k] = f"{v/100:.2f}"
        elif isinstance(v, float):
            ret[k] = f"{v:.3f}"
        elif not isinstance(v, str):
            ret[k] = f"{v}"
        else:
            ret[k] = v
    return ret

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print(f"""Usage: python3 {sys.argv[0]} [systematic|scalable] <case_dirs>""")
        exit(1)

    if not sys.argv[1] in ['systematic', 'scalable']:
        print("Usage error: second argument must be one of 'systematic' or 'scalable'")
        exit(1)

    if os.path.isfile(sys.argv[2]) and sys.argv[2].endswith(".csv"):
        exit(1) # FIXME read from csv
    elif os.path.isdir(sys.argv[2]):
        case_name_regex = CASE_NAME_SYSTEMATIC_REGEX if sys.argv[1] == 'systematic' else CASE_NAME_SCALABLE_REGEX
        cases_records = read_data_from_result_stdouts(sys.argv[2:], case_name_regex)
    else:
        print(f"Not a directory: {sys.argv[2]}, exiting")
        exit(1)

    assert cases_records, "Failed to read input directories"

    print(','.join(HEADER))   # headers
    for stat in cases_records:
        stat_str = format_stat_record(stat)
        print(','.join([ stat_str.get(h, "") for h in HEADER ]))

