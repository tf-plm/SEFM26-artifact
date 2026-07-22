# Usage (F1)

The `synthetic_case_gen.py` file is the code to generate our systematic benchmarks. Run it in a Docker container, c.f. `../README.md`.

## Systematic benchmark of all possible cases

* Create an output directory, e.g. `mkdir bench-systematic`.
* Run `python3 synthetic_case_gen.py systematic -n <n> <output_path>` with `<n>` between 2 and 4 and `<output_path>` the path where the cases will be generated.

The generated cases for 2 and 3 resources are already provided in `cases_same2.tar.gz` and `cases_same3.tar.gz`.

## Scalable benchmark for different topologies

* Create an output directory, e.g. `mkdir bench-scalable`.
* Run `python3 synthetic_case_gen.py scalable <output_path>` with `<output_path>` the path where the cases will be generated.

The generated cases are already provided in `cases_scalable5.tar.gz`, `cases_scalable15-25.tar.gz` and `cases_scalable30-50.tar.gz`.

# Details on the scalable benchmark

## Parameters

* Topology
    * (a) simple
        * 2 groups, 1-1 links
    * (b) butterfly
        * 2 groups, n-1-n links
    * (c) diamond
        * 1 group, 1-n-1 links
    * (d) chain
        * 1 "group", 1-1 links

* Number of resources, equally divided in each group of n resources
    * 6
    * 10
        * (a) 5, 5
        * (b) 5, 1, 5
        * (c) 1, 10, 1
        * (d) 10
    * 20

* Distribution of diff operations (NOOP, UPDATE, C-D, D-C), globally
    * 70%, 10%, 10%, 10%
    * 40%, 20%, 20%, 20%
    * rotate -- Total of 8 samples

* For topologies (a) and (b), distribution of change operations (UPDATE, C-D, D-C) per groups (top and bottom)
    * 50%-50%
    * 80%-20%
    * 20%-80%

* For topologies (b) and (c), diff operation for the unique-resource-stage
    * (b) middle stage: 4 operations
    * (c) top and bottom stages: 4*2 operations


Total number of parameter sets for each topology:

* (a) 3 (# of resources) * 8 (ops distribution globally) * 3 (ops distribution per groups) = 72
* (b) 3 (# of resources) * 8 (ops distribution globally) * 3 (ops distribution per groups) * 4 (middle resource operation) = 288
* (c) 3 (# of resources) * 8 (ops distribution globally) * 4*4 (top and bottom resource operation) = 384
* (d) 3 (# of resources) * 8 (ops distribution globally) = 24

Total is 72 + 288 + 384 + 24 = 768, repeated twice.

## Naming scheme

* (a) `simple{n}-{principal_op_percentage}{principal_op}-{top_changes_percentage}{bot_changes_percentage}`
    * e.g. `simple5-70pNOOP-8020`
* (b) `butterfly{n}-{principal_op_percentage}{principal_op}-mid{mid_op}-{top_changes_percentage}{bot_changes_percentage}`
    * e.g. `butterfly10-70pUPDATE-midCD-5050`
* (c) `diamond{n}-{principal_op_percentage}{principal_op}-top{top_op}-bot{bot_op}`
    * e.g. `diamond20-40pDC-topUPDATE-botNOOP`
* (d) `chain{n}-{principal_op_percentage}{principal_op}`
    * e.g. `chain5-40pCD`

