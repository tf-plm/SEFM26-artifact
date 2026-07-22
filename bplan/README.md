
# Usage

Programs in this directory should be run in a Docker container.

```
docker build . -t bplan
docker run -it bplan
```

# Directory description

* `src/` contains the Python source files of BPlan, it relies on the Maude semantics in `semantics/`.

* `semantics/` contains our Maude implementation of Terraform's semantics.

* `real-modules/` (F4) contains the Terraform modules extracted from TerraDS.

* `synthetic-cases/` (F1) contains the script to generate our benchmarks as well as `.tar.gz` files of the benchmarks (excluding the systematic cases with 4 resources) and the results in CSV.

* `scripts/` (F2, F3) contains various scripts, see `scripts/README.md`.

