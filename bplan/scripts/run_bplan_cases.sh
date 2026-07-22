#!/bin/bash

cat $0
# cat hosts.txt || exit
# source ./install-exp.sh


# parallel \
#     --sshloginfile=hosts.txt \
#     --nonall \
#     --workdir=$(pwd) \
#     ./install-exp.sh

bench_dirs=$@
printf "%s\n" $bench_dirs
timeout=$((15*60))
logdir=$(dirname $(dirname $1))
bplanscript="$(dirname $0)/../src/bplan.py"

all_bplan_args=(
    # 'parse' \
    # 'schedule' \
    # 'check stable res' \
    'check stable dep' \
    # 'check not-unstable'\
)
for args in "${all_bplan_args[@]}"; do
    log_parallel=${logdir}/log_parallel_bplans_${args// /-}_$(date +"%b%d-%H%M%S").txt
    log_bplans=${logdir}/log_bplans_${args// /-}_$(date +"%b%d-%H%M%S").txt
    echo "Log parallel: $log_parallel"
    echo "Log BPlan: $log_bplans"
    parallel \
        --joblog "${log_parallel}"\
        --timeout=$timeout \
        "python3 $bplanscript" $args ::: $bench_dirs \
        > "${log_bplans}"
done
        # --sshloginfile=hosts.txt \

# END
