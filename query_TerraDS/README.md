

## 1. Get TerraDS with 

Download TerraDS database from Zenodo with the following command:

```bash
curl https://zenodo.org/records/14217386/files/TerraDS.sqlite -o TerraDS.sqlite
```

## 2. Generate stats about the number of used ressources in Terraform deployment

### 2.1 Create CSV files with data

The following will generate:
- `resource_distribution.csv` : number of resources by repository
- `module_resource_distribution.csv` : number of modules by module

#### 2.1.1 Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 2.1.2 Install Python dependencies

```bash
pip install -r requirements.txt
```

#### 2.1.3 Run the Python script

```bash
python stats.py
```

### 2.2 Generate plots from these data

After `resource_distribution.csv` and `module_resource_distribution.csv` have been created, use R to generate the plots.

```bash
Rscript plots.r
```

### Run the R Markdown version (interactive)

If you prefer to run the construction interactively:

1. Open **RStudio**
2. Open `Plots.Rmd`
3. Click **Knit** to run the entire document  
   or run each chunk step by step using the **Run** button.

## 3. Find candidate for testing BPlan

```bash
python find_repo.py
```

