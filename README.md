
We claim two badges: _Available_ and _Functional_

# Functional outcomes

* F1: Generating our benchmarks (Sections 5.1 and 5.2). See `bplan/synthetic-cases/README.md`.
* F2: Validating the correctness of BPlan w.r.t. Terraform traces (Sections 5.1 and 5.2). See `bplan/scripts/README.md`.
* F3: Scalability results of BPlan on our benchmark (Table 1). See `bplan/scripts/README.md`.
* F4: Scalability results of BPlan on real Terraform modules (Table 3). See `bplan/real_modules/README.md`.

# Directory structure

Each directory contains a nested `README.md` for further details.

* `bplan/` is the main subdirectory containing the source code of BPlan with the Maude semantics as well as the code for generating our benchmarks, the Terraform code of real modules and their changes, and scripts for BPlan correctness validations.
* `query_TerraDS/` contains the code to count the number of resources in TerraDS, as shown in Table 2.
* `TerraDS-exploration/` contains the code to extract critical commits as explained in Section 5.3. The extraction may take several hours (even days if not parallelized).
