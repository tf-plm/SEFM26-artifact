# Usage (F4)

In the docker image (c.f. `../README.md`)

* Navigate in the BPlan source directory: `cd /bplan/src/`
* For a real module directory `<module>`, run `time python3 bplan.py check stable dep ../real-modules/<module>/plan_stable.json` to time the model-checking of the stable change.
* Replace `plan_stable.json` with `plan_estable.json` to time the eventually stable change.


# Selected repos and changes

The modules were exported from TerraDS, see `query_TerraDS/` at the root of the artifact for the extraction process.
From exported modules, we have selected five and adapted them to be able to run `terraform plan` to produce the initial plan `plan_init.json`. Then,

* `plan_change0.json` is the result of running `python3 copy_config_as_state.py <module>/plan_init.json | jq > <module>/plan_change0.json`
* and `plan_{stable,estable}.json` are the `plan_change0.json` where we have manually changed the `create` actions.


## Crown-Commercial-Service/digitalmarketplace-aws :: terraform/modules/router

* n = 7
* Topology is n -> 1
    * like diamond and top, no bottom
* changes add a replacement operation to `aws_route53_zone.root` and either NOOP or UPDATE on the others
* `plan_stable.json`
    * CREATE-DELETE aws_route53_zone.root
    * UPDATE on the 3 others
* `plan_estable.json`
    * DELETE-CREATE aws_route53_zone.root
    * UPDATE on the 3 others

## ploio/hyperion-k8s :: terraform/openstack

* n = 8
* Topology is 2 levels
    * like bipartite but degree of nodes is between 0 and 3
* `plan_stable.json`
    * DELETE-CREATE on `openstack_networking_network_v2.hyperion-network`
    * UPDATE on 3 coreferences
    * NOOP on 4 others
* `plan_estable.json`
    * same as `plan_estable.json` but DELETE-CREATE

## govuk-infrastructure :: terraform/deployments/vpc

* n = 12
* Topology is 3 level
    * bipartite with degree between 0 and 2;
    * plus diamond-top to `aws_vpc.vpc`
* Changes per level is
    1. CREATE-DELETE for `plan_stable.json` and DELETE-CREATE for `plan_estable.json` on top and NOOP on 3 others
    1. UPDATE on 3 out of 5 codependencies of top, NOOP on 2 others
    1. UPDATE on 2 ouf of 4 codependencies of the 2nd level, NOOP on 2 others

## n=31 - smarla/core-network :: infra/terraform

* n = 31
* Topology is has 5 layers, from top to bottom `[ 2 <- 5 <- 8 <- 9 <- 7 ]`
* Change is one DC, 4 update
    * CREATE-DELETE for `plan_stable.json` and DELETE-CREATE for `plan_estable.json` on api_connect
    * update on auth, login, login ok, login ko, ko_integr, ok_integr resources

## n=48 - Laxman-SM/terraform-mesos-aws :: modules/demo/network/vpc

* Topology is complex with 6 layers, from top to bottom `[ 1 <- 2 <- 3 <- 20 <- 21 <- 2 ]`
* Change is CREATE-DELETE for `plan_stable.json` and DELETE-CREATE for `plan_estable.json` on the top resource and UPDATE on 3 others.

