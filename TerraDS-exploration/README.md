All the process below describes how we obtained `critical_changes.sqlite` file.
For reproducibility reasons, all the steps are documented, but users can only consider `critical_changes.sqlite` to explore.

## Initialize 

Run `init.sh` script
- Initialize a virtual environment for Pyhton
- Download TerraDS.sqlite

## Commit downloader

### Locally

- The current scrapper uses Github accesses for getting past commits. Because of that, user must generate tokens (see https://github.com/settings/personal-access-tokens). Several tokens might be useful to face scalability issue and cooling time between queries.
All the tokens must be placed in `tokens.txt` file (1 per line).

- Start the virtual environment with `source .venv/bin/activate`, and then run `python3 commit_explorer.py`

- Note: You can download a specific number of module history using the `-n` option. Otherwise, you will get commits for 181451 modules.
For instance, `python3 scrap_commits.py -n 10` will get the history of 10 Terraform modules.

### On Grid5000 with EnosLib

To speed up this process, it is possible to run the script on Grid5000. `scrap_with_enoslib.py` is a script using EnosLib to provision resources on Grid5000 and run the script. 
Once finished (around 12h05), a tar file is generated with all commits history. It can be downloaded locally with 

```bash
scp -J username@access.grid5000.fr username@rennes:/home/username/TerraDS_commit_explorer/all_module.tar .
```

Sure, replace `username` with your g5k identifier

## Find exploitable cases

### Locally

- The current analyzer takes the obtained tar from commit downloader step. Because of that, a jar containing modules must be present. 

- Start the virtual environment with `source .venv/bin/activate`, and then run `python process_commits.py`

- Note: You can give a specific number of threads to distribute the analysis, with option `-nw`. Also, the name of tar file can be changed, and the option `-tar` allows to specify the archive to analyze.
For instance, `python process_commits.py -nw 16 -tar my_modules.tar` will proceed the analysis of modules on on `my_modules.tar` using 16 threads.

### On Grid5000 with EnosLib

To speed up this process, it is possible to run the script on Grid5000. `commits_with_enoslib.py` is a script using EnosLib to provision resources on Grid5000 and run the script. 
Once finished (around 5h), a json file is generated. It can be downloaded locally with 
```bash
scp -J username@access.grid5000.fr username@rennes:/home/username/TerraDS_commit_explorer/critical_changes.json .
```

### Using a container

If you did not run `init.sh`, you must first build the image:
```bash
docker build -t image_process_commit:latest .
```

Then, you can process the analysis with:
```bash
docker run -it --name commit_explorer_container image_process_commit:latest
```

- Note: If you modify the Dockerfile, you must rebuild the image.
    You will have to stop and destroy your previous container with
    ```docker rm -f commit_explorer_container``` 
    and re-execute above commands

Once the process ended, you will have to get the result file from the container with the following command:
```bash
docker cp commit_explorer_container:/app/critical_changes.json ./critical_changes.json
```

## Convert JSON results to SQLite

Once the analysis process has ended and the `critical_changes.json` file has been generated, you can convert this JSON data into a structured SQLite database for easier querying and exploration.

The python script `convert_json_to_sql.py` contains the conversion logic. Ensure both the script and your `critical_changes.json` are in the same directory, then run:

```bash
python3 json_to_sqlite.py
```

You can open and interact with the generated SQLite database directly from your terminal using the SQLite command-line interface:

```bash
sqlite3 database.sqlite
```

Note: Once in the SQLite interface, the schema of the database can be displayed with `.schema`

### Examples of queries

- Count the total number of modules
```sql
SELECT COUNT(*) AS TotalModules 
FROM Modules;
```

- Find changes in modules with 10 resources (5 results):
```sql
SELECT 
    m.Repository, m.ModulePath, 
    c.ShaCommitOld, c.ShaCommitNew
FROM Modules m JOIN Changes c ON m.Id = c.IdModule
WHERE c.NumberOfResources = 10 LIMIT 5;
```

