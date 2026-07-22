Except for the first one, run these scripts in a Docker container, c.f. `../README.md`.

* `install-exp.sh` installs the dependencies required to run BPlan and the benchmarks (already executed as part of the Docker image build).

* (F2) `validate_trace.py` is the script that validates the correctness w.r.t. Terraform traces of (1) our action graph with a topological sort algorithm and (2) the execution rules using Maude's `search` command.
    1. For a directory `<cases>` containing subdirectories of all cases to validate (c.f. `../systematic-cases/README.md` to generate the cases),
    1. Run `python3 validate_trace actiongraph <cases>` to validate the action graph,
    1. And run `python3 validate_trace execrules <cases>` to validate the rules.

* (F3.1) `run_bplan_cases.sh` is a helper script to run BPlan on multiple cases in parallel.
    1. For a directory `<cases>` containing subdirectories of all cases,
    1. Run `./run_bplan_cases.sh <cases>/*` to run BPlan on all cases. The outcomes are written in a `bplans/` subdirectory for each case.

* (F3.2) `explore_bench_results.py` is the script that aggregates the execution times of BPlan runs in CSV format. It relies on the log files generated in the subdirectories `bplans/` of each test case after a BPlan run. To generate the columns, the script relies on the naming scheme of the case subdirectories for our two benchmarks: either `systematic` or `scalable`. The summary for our benchmarks are already available in `../synthetic-cases/results/*.csv`.
    1. For the systematic benchmark, run `python3 explore_bench_results.py systematic <systematic_cases>/*`.
    1. And run `python3 explore_bench_results.py scalable <scalable_cases>/*` to aggregate the scalable benchmark runs.
