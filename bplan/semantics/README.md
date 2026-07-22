
* `syntactic.maude` contains the model, defining the shape of the rewritten configuration $(T, \pi, \Sigma, \mathcal{A}, \Delta)$
* `semantics.maude` contains the main semantic functions and rules. It also defines strategies that respectively group the planning and execution rules.
* `check.maude` contains the _dangling_ and _duplicate_ predicates as well as the LTL stability formulas.
* `tuples.maude` is the library of parametrized tuples and sets of tuples, used as our basic notation.
* `sorts.maude` defines basic sorts separately because they need a `view` mapping in order to use them in collections.
* `main.maude` loads the above files and serves as the main entrypoint.

