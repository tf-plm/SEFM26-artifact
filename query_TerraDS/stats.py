from collections import Counter
import csv
import sqlite3

conn = sqlite3.connect("TerraDS.sqlite")
cursor = conn.cursor()

# ----------------------------------
# 1) RESSOURCES PAR REPOSITORY
# ----------------------------------

query1 = """
SELECT r.Id AS RepositoryId, COUNT(res.Id) AS ResourceCount
FROM Repositories r
LEFT JOIN Modules m ON m.RepositoryId = r.Id
LEFT JOIN Resources res ON res.ModuleId = m.Id
GROUP BY r.Id;
"""

cursor.execute(query1)
repo_resource_counts = {repo_id: count for repo_id, count in cursor.fetchall()}

resource_counts = list(repo_resource_counts.values())
count_by_resource_number = Counter(resource_counts)

with open("resource_distribution.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["resource_count", "repository_count"])
    for resource_count, repo_count in sorted(count_by_resource_number.items()):
        writer.writerow([resource_count, repo_count])

# ----------------------------------
# 2) RESSOURCES PAR MODULE
# ----------------------------------

query2 = """
SELECT m.Id AS ModuleId, COUNT(res.Id) AS ResourceCount
FROM Modules m
LEFT JOIN Resources res ON res.ModuleId = m.Id
GROUP BY m.Id;
"""

cursor.execute(query2)
module_resource_counts = {module_id: count for module_id, count in cursor.fetchall()}

module_counts = list(module_resource_counts.values())
count_by_resource_per_module = Counter(module_counts)

with open("module_resource_distribution.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["resource_count", "module_count"])
    for resource_count, module_count in sorted(count_by_resource_per_module.items()):
        writer.writerow([resource_count, module_count])

conn.close()