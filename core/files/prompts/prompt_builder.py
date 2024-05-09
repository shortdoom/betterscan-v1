import argparse
import csv
import json
import os

# python script.py prompt_template.txt --csv_file (optional) extra_data.csv --json_file prompt.json
# beware that some manual review's still required (ie. editing response_name if you are building response-template)

def load_prompt_template(txt_filename):
    with open(txt_filename, 'r') as file:
        return file.read().strip()

def load_extra_data(csv_filename):
    if not csv_filename:
        return [{}]

    extra_data = {}
    with open(csv_filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip the header row if present
        for row in reader:
            if len(row) >= 2:
                extra_data[row[0]] = row[1]
    return [extra_data]

def update_json_file(json_filename, new_data):
    if not os.path.exists(json_filename):
        with open(json_filename, 'w') as jsonfile:
            json.dump([new_data], jsonfile, indent=4)
    else:
        with open(json_filename, 'r') as jsonfile:
            data = json.load(jsonfile)
            data.append(new_data)
        with open(json_filename, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=4)

def main(args):
    prompt_template = load_prompt_template(args.txt_file)
    extra_data = load_extra_data(args.csv_file)
    name = os.path.splitext(os.path.basename(args.txt_file))[0]
    
    new_json_data = {
        "name": name,
        "response_name": name + "_response",
        "prompt_template": prompt_template,
        "extra_data": extra_data
    }

    update_json_file(args.json_file, new_json_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update JSON file with data from TXT and optionally CSV files.")
    parser.add_argument("txt_file", help="Path to the TXT file containing the prompt template")
    parser.add_argument("--csv_file", default=None, help="Optional path to the CSV file containing the extra data")
    parser.add_argument("--json_file", default="prompt.json", help="Path to the JSON file to be updated (default: prompt.json)")

    args = parser.parse_args()
    main(args)
