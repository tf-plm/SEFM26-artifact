import json
import sqlite3

def json_to_sqlite(json_filepath, db_filepath):
    conn = sqlite3.connect(db_filepath)
    cursor = conn.cursor()

    # Create the tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS "Modules" (
            "Id" INTEGER NOT NULL CONSTRAINT "PK_Modules" PRIMARY KEY AUTOINCREMENT,
            "IdTerraDS" INTEGER NOT NULL, 
            "Repository" TEXT NOT NULL,
            "ModulePath" TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS "Changes" (
            "Id" INTEGER NOT NULL CONSTRAINT "PK_Changes" PRIMARY KEY AUTOINCREMENT,
            "IdModule" INTEGER NOT NULL, 
            "ShaCommitOld" TEXT NOT NULL,
            "ShaCommitNew" TEXT NOT NULL,
            "NumberOfResources" INTEGER
        );
        CREATE TABLE IF NOT EXISTS "Attributes" (
            "Id" INTEGER NOT NULL CONSTRAINT "PK_Attributes" PRIMARY KEY AUTOINCREMENT,
            "IdChange" INTEGER NOT NULL, 
            "Provider" TEXT NOT NULL,
            "ResourceType" TEXT NOT NULL,
            "ResourceName" TEXT NOT NULL,
            "AttributeName" TEXT NOT NULL
        );
    """)

    with open(json_filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)

    for ds_id_str, module_data in data.items():
        id_terra_ds = int(ds_id_str)
        repository = module_data.get("repository", "")
        module_path = module_data.get("module_path", "")
        
        cursor.execute(
            'INSERT INTO "Modules" ("IdTerraDS", "Repository", "ModulePath") VALUES (?, ?, ?)',
            (id_terra_ds, repository, module_path)
        )
        id_module = cursor.lastrowid

        # Loop through the changes for this module
        for change in module_data.get("changes", []):
            sha_old = change.get("sha_old", "")
            sha_new = change.get("sha_new", "")
            num_resources = change.get("number_of_resources", 0)

            cursor.execute(
                'INSERT INTO "Changes" ("IdModule", "ShaCommitOld", "ShaCommitNew", "NumberOfResources") VALUES (?, ?, ?, ?)',
                (id_module, sha_old, sha_new, num_resources)
            )
            
            id_change = cursor.lastrowid
            for attr in change.get("resource_attributes", []):
                provider = attr.get("provider", "")
                resource_type = attr.get("type", "")
                resource_name = attr.get("name", "")
                attribute_name = attr.get("attribute", "")
                
                # Insert into Attributes table
                cursor.execute(
                    'INSERT INTO "Attributes" ("IdChange", "Provider", "ResourceType", "ResourceName", "AttributeName") VALUES (?, ?, ?, ?, ?)',
                    (id_change, provider, resource_type, resource_name, attribute_name)
                )
    conn.commit()
    conn.close()
    
    print(f"Data successfully imported into {db_filepath}")

if __name__ == "__main__":
    input_json = 'critical_changes.json'
    output_db = 'critical_changes.sqlite'
    json_to_sqlite(input_json, output_db)

