import os
import re
import sqlite3
import subprocess
from collections import defaultdict

DB_PATH = "TerraDS.sqlite"
CLONE_BASE_DIR = "cloned_repos"   # where we put git clones
MAX_PAIRS_PER_QUERY = 5

FOR_EACH_PATTERN = re.compile(r"\bfor_each\b")
DATA_BLOCK_PATTERN = re.compile(
    r'^\s*data\s+"[^"]+"\s+"[^"]+"\s*\{',
    re.MULTILINE,
)
MODULE_BLOCK_PATTERN = re.compile(
    r'^\s*module\s+"[^"]+"\s*\{',
    re.MULTILINE,
)

query40_50 = """
SELECT 
    r.FullName  AS RepositoryName,
    m.Path      AS ModulePath,
    r.Id        AS RepositoryId,
    COUNT(res.Id) AS ResourceCount
FROM Modules m
JOIN Repositories r ON r.Id = m.RepositoryId
LEFT JOIN Resources res ON res.ModuleId = m.Id
WHERE LENGTH(m.ModuleCalls) <= 20
GROUP BY 
    m.Id,
    m.Path,
    r.Id,
    r.FullName
HAVING COUNT(res.Id) <= 50 AND COUNT(res.Id) > 40 ;
"""

query30_40 = """
SELECT 
    r.FullName  AS RepositoryName,
    m.Path      AS ModulePath,
    r.Id        AS RepositoryId,
    COUNT(res.Id) AS ResourceCount
FROM Modules m
JOIN Repositories r ON r.Id = m.RepositoryId
LEFT JOIN Resources res ON res.ModuleId = m.Id
WHERE LENGTH(m.ModuleCalls) <= 20
GROUP BY 
    m.Id,
    m.Path,
    r.Id,
    r.FullName
HAVING COUNT(res.Id) <= 40 AND COUNT(res.Id) > 30 ;
"""

query20_30 = """
SELECT 
    r.FullName  AS RepositoryName,
    m.Path      AS ModulePath,
    r.Id        AS RepositoryId,
    COUNT(res.Id) AS ResourceCount
FROM Modules m
JOIN Repositories r ON r.Id = m.RepositoryId
LEFT JOIN Resources res ON res.ModuleId = m.Id
WHERE LENGTH(m.ModuleCalls) <= 20
GROUP BY 
    m.Id,
    m.Path,
    r.Id,
    r.FullName
HAVING COUNT(res.Id) <= 30 AND COUNT(res.Id) > 20 ;
"""

query10_20 = """
SELECT 
    r.FullName  AS RepositoryName,
    m.Path      AS ModulePath,
    r.Id        AS RepositoryId,
    COUNT(res.Id) AS ResourceCount
FROM Modules m
JOIN Repositories r ON r.Id = m.RepositoryId
LEFT JOIN Resources res ON res.ModuleId = m.Id
WHERE LENGTH(m.ModuleCalls) <= 20
GROUP BY 
    m.Id,
    m.Path,
    r.Id,
    r.FullName
HAVING COUNT(res.Id) <= 20 AND COUNT(res.Id) > 10 ;
"""

query00_10 = """
SELECT 
    r.FullName  AS RepositoryName,
    m.Path      AS ModulePath,
    r.Id        AS RepositoryId,
    COUNT(res.Id) AS ResourceCount
FROM Modules m
JOIN Repositories r ON r.Id = m.RepositoryId
LEFT JOIN Resources res ON res.ModuleId = m.Id
WHERE LENGTH(m.ModuleCalls) <= 20
GROUP BY 
    m.Id,
    m.Path,
    r.Id,
    r.FullName
HAVING COUNT(res.Id) <= 10 AND COUNT(res.Id) > 0 ;
"""

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def repo_clone_path(repo_fullname: str) -> str:
    """
    Local directory name for a given repo full name.
    """
    safe_name = repo_fullname.replace("/", "__")
    return os.path.join(CLONE_BASE_DIR, safe_name)

def clone_repo(repo_fullname: str) -> str:
    """
    Clone the repo from GitHub if not already cloned.
    Assumes repo_fullname is 'owner/repo'.
    Returns the local path to the repo.
    """
    ensure_dir(CLONE_BASE_DIR)
    dest = repo_clone_path(repo_fullname)

    if os.path.isdir(dest) and os.path.isdir(os.path.join(dest, ".git")):
        return dest

    clone_url = f"https://github.com/{repo_fullname}.git"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, dest],
            check=True,
        )
    except subprocess.CalledProcessError:
        return None

    return dest


def valid_module(repo_dir: str, module_path: str) -> bool:
    """ 
    A module is considered valid for our experiments iff there is no for_each;
    nor non-supported blocks:

      - data "*" "*" {
      - module "*" {
    """
    abs_module_path = os.path.join(repo_dir, module_path)
    if not os.path.exists(abs_module_path):
        return False

    tf_files = []
    if os.path.isfile(abs_module_path):
        # If ModulePath is a file, check that file only if it's .tf
        if abs_module_path.endswith(".tf"):
            tf_files.append(abs_module_path)
        else:
            return False
    else:
        for root, _, files in os.walk(abs_module_path):
            for name in files:
                if name.endswith(".tf"):
                    tf_files.append(os.path.join(root, name))

    if not tf_files:
        return False

    for tf in tf_files:
        try:
            with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                if (FOR_EACH_PATTERN.search(content) or 
                    DATA_BLOCK_PATTERN.search(content) or 
                    MODULE_BLOCK_PATTERN.search(content)): 
                    return False   

                # Extra safety: reject any 'data' or 'module' usage at all
                if "data" in content:
                    return False
                if "module" in content:
                    return False

        except Exception:
            return False

    # All .tf files had none of the forbidden patterns
    return True 


def fetch_modules_grouped_by_repo(cursor, sql: str):
    """
    Returns:
      dict: repo_fullname -> list of (module_path, resource_count)
    so we keep the resource count associated with each module.
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    by_repo = defaultdict(list)
    for repo_name, module_path, repo_id, resource_count in rows:
        by_repo[repo_name].append((module_path, resource_count))
    return by_repo


def process_query(cursor, sql: str, label: str, max_pairs: int = MAX_PAIRS_PER_QUERY):
    """
    For a given query:
    - group rows by repo
    - clone repos
    - check each module's .tf files
    - collect up to max_pairs (repo, module_path) with no forbidden constructs

    Returns:
      skipped_pairs: list[(repo, module)]
      valid_pairs:   list[(repo, module)]
      resource_counts: dict[(repo, module) -> resource_count] for valid pairs
    """
    by_repo = fetch_modules_grouped_by_repo(cursor, sql)
    valid_pairs = []
    skipped_pairs = []
    resource_counts = {}  # key: (repo_fullname, module_path) -> resource_count

    for repo_fullname, modules in by_repo.items():
        if len(valid_pairs) >= max_pairs:
            break

        repo_dir = clone_repo(repo_fullname)
        if repo_dir is None:
            continue

        for module_path, resource_count in modules:
            if len(valid_pairs) >= max_pairs:
                break

            if valid_module(repo_dir, module_path):
                valid_pairs.append((repo_fullname, module_path))
                resource_counts[(repo_fullname, module_path)] = resource_count
            else:
                skipped_pairs.append((repo_fullname, module_path))

    return skipped_pairs, valid_pairs, resource_counts


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    queries = [
        ("40 < resources <= 50", query40_50),
        ("30 < resources <= 40", query30_40),
        ("20 < resources <= 30", query20_30),
        ("10 < resources <= 20", query10_20),
        ("00 < resources <= 10", query00_10),
    ]

    all_results = {}        # label -> (valid_pairs, resource_counts dict)
    total_skipped = 0

    for label, sql in queries:
        skipped_pairs, valid_pairs, resource_counts = process_query(
            cursor, sql, label, max_pairs=MAX_PAIRS_PER_QUERY
        )
        total_skipped += len(skipped_pairs)
        all_results[label] = (valid_pairs, resource_counts)

    conn.close()

    print("====== SUMMARY ======")
    print(f"skipped {total_skipped} modules ")
    print("=====================")
    print("repository :: module (resources)")
    print("=====================")
    for label, (pairs, resource_counts) in all_results.items():
        print(f"\n{label}:")
        for repo, module in pairs:
            n_res = resource_counts.get((repo, module))
            print(f"  - {repo} :: {module}  [resources={n_res}]")

if __name__ == "__main__":
    main()
