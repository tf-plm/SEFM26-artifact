from enoslib import *
from enoslib.infra.enos_g5k.g5k_api_utils import get_api_username

username = get_api_username()
# Use the absolute path to ensure the node finds your files
project_dir = f"/home/{username}/Project/TerraDS_commit_explorer"

site = "rennes"
cluster = "paradoxe"
job_name = "GH Terraform"
walltime = "13:00:00"
start_time = "2026-03-09 19:00:00"

network = G5kNetworkConf(id="prod_net", type="prod", roles=["net"], site=site)
g5k = G5kConf.from_settings(job_type="allow_classic_ssh", job_name=job_name, walltime=walltime,reservation=start_time)
g5k.add_network_conf(network).add_machine(roles=["GH"], cluster=cluster, nodes=1, primary_network=network)

conf = g5k.finalize()
provider = G5k(conf)
roles, networks = provider.init()

address = roles["GH"][0].address
print(f"Booked {address} for {walltime}")

with play_on(pattern_hosts="GH", roles=roles) as p:
    p.shell(f"cd {project_dir} && chmod +x init.sh && ./init.sh")
    p.shell(f"cd {project_dir} && ./.venv/bin/python commit_explorer.py")
    p.shell(f"ls -lh {project_dir}/all_module.tar")
print(f"Process finished. You can find your results in: {project_dir}/all_module.tar")

provider.destroy()