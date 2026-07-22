#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys

import tf2maude

# read the JSON plan in argument
tfplan_path = sys.argv[1]
with open(tfplan_path, 'r') as f:
    tfplan = json.load(f)

# get target resources JSON dict and parse its dependencies
config_tfresources = tfplan["configuration"]["root_module"].get("resources",[])
target_graph = tf2maude.extract_target_dependencies(config_tfresources)

# convert target to state resources
state_tfresources = list()
for tfres in config_tfresources:
    tfres.pop("schema_version")
    tfres.pop("expressions", {})
    tfres.update({ "depends_on": [] })
    for ds in target_graph.get("'" + tfres["address"], []):
        tfres["depends_on"].append(ds[1:])
    state_tfresources.append(tfres)

# print(target_graph)
new_tfplan = tfplan.copy()
new_tfplan["prior_state"] = {
    "format_version": "1.0",
    "terraform_version": "1.13.1",
    "values": {
        "outputs": {},
        "root_module": {
            "resources": state_tfresources
        }
    }
}

print(json.dumps(new_tfplan))
