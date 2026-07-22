from enoslib import *
from enoslib.infra.enos_g5k.g5k_api_utils import get_api_username

username = get_api_username()
# Use the absolute path to ensure the node finds your files
project_dir = f"/home/{username}/Project/TerraDS_commit_explorer"

site = "rennes"
cluster = "paradoxe"
job_name = "GH Terraform - process"
walltime = "02:00:00"
# start_time = "2026-03-18 20:00:00"

network = G5kNetworkConf(id="prod_net", type="prod", roles=["net"], site=site)
g5k = G5kConf.from_settings(job_type="allow_classic_ssh", job_name=job_name, walltime=walltime,
                            #reservation=start_time
                            )
g5k.add_network_conf(network).add_machine(roles=["GH"], cluster=cluster, nodes=1, primary_network=network)

conf = g5k.finalize()
provider = G5k(conf)
roles, networks = provider.init()

address = roles["GH"][0].address
print(f"Booked {address} for {walltime}")

# with play_on(pattern_hosts="GH", roles=roles) as p:
#     p.shell(f"cd {project_dir} && chmod +x init.sh && ./init.sh")
#     # p.shell(f'cd {project_dir} && curl -L -O -J "https://filesender.renater.fr/download.php?token=1b00bae6-dc9a-4935-8e92-9598d5e78370&files_ids=68208590"')
#     p.shell(f"cd {project_dir} && ./.venv/bin/python process_commits.py")
#     p.shell(f"ls -lh {project_dir}/critical_changes.json")
# print(f"Process finished. You can find your results in: {project_dir}/critical_changes.json")

# provider.destroy()