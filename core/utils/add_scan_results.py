import os
import json
import sqlite3


def connect_to_database(db_path):
    """Connect to the SQLite database at the given path."""
    conn = sqlite3.connect(db_path)
    return conn


def process_file(cursor, filepath):
    """Process a single JSON file and insert its data into the scan_results table."""
    with open(filepath, "r") as file:
        data = json.load(file)
        scan_results = data.get("scan_results", [])
        network_info = data.get("network_info", {})
        target = f"{network_info.get('Network', '')}:{network_info.get('Address', '')}"

        for result in scan_results:
            # Using .get() method with a default value of 'Unknown' or an appropriate default
            check_type = result.get("check", "Unknown")
            confidence = result.get("confidence", "Unknown")
            contract = result.get("contract", "Unknown")
            description = result.get("description", "No description provided")
            expressions = json.dumps(result.get("expressions", []))
            full_name = result.get("full_name", "No name provided")
            impact = result.get("impact", "No impact provided")

            print(f"Inserting {full_name} into the database")

            try:
                cursor.execute(
                    "INSERT INTO scan_results (check_type, confidence, contract, description, expressions, full_name, impact, target) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        check_type,
                        confidence,
                        contract,
                        description,
                        expressions,
                        full_name,
                        impact,
                        target,
                    ),
                )
            except sqlite3.IntegrityError as e:
                print(f"An integrity error occurred: {e}")


def main():
    
    script_path = os.path.dirname(os.path.realpath(__file__))
    db_path = os.path.join(
        script_path, "..", "..", "immunefi-terminal", "datasette", "immunefi_data.db"
    )

    conn = connect_to_database(db_path)
    c = conn.cursor()

    for root, dirs, files in os.walk("out"):
        for file in files:
            if file == "sessionData.json":
                print(f"Processing {root}/{file}")
                process_file(c, os.path.join(root, file))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
