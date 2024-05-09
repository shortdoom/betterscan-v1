import requests
import sqlite3
import argparse
import time
import json
import os
import csv

"""
Loads targets from the db and sends it to the app

core/targets_run.py --bountyId <name>

requires app.py to be running on 127.0.0.1:5000

"""
app_dir = os.path.dirname(os.path.realpath(__file__))
LOCAL_DB_PATH = os.path.join(
    app_dir, "..", "..", "immunefi-terminal", "datasette", "immunefi_data.db"
)
TARGETS_DIRECTORY = os.path.join(app_dir, "files", "out")


def connect_db():
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    return conn, cursor


def get_all_target():
    conn, cursor = connect_db()
    cursor.execute("SELECT target FROM targets")
    targets = [item[0] for item in cursor.fetchall()]
    conn.close()
    return targets


def get_targets(bountyId):
    conn, cursor = connect_db()
    cursor.execute(
        "SELECT target FROM targets WHERE bountyId = ? AND target NOT LIKE '%unknown%'",
        (bountyId,),
    )
    targets = [item[0] for item in cursor.fetchall()]
    conn.close()
    return targets


def check_if_exists(path):
    conn, cursor = connect_db()
    cursor.execute("SELECT EXISTS(SELECT 1 FROM targets_data WHERE target=?)", (path,))
    exists = cursor.fetchone()[0]
    conn.close()
    return exists == 1


from collections import deque


def post_to_app(targets):
    url = "http://127.0.0.1:5000/"
    timestamps = deque(maxlen=5)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    if isinstance(targets, str):
        targets = [targets]

    for target in targets:
        while len(timestamps) == 5 and time.time() - timestamps[0] < 1:
            time.sleep(1 - (time.time() - timestamps[0]))

        if len(timestamps) == 5:
            timestamps.popleft()

        timestamps.append(time.time())

        payload = "path={}&api_key=".format(target)
        print("Executing payload:", payload)

        try:
            response = requests.post(url, data=payload, headers=headers)
            if response.status_code == 200:
                save_response_to_directory(target[0], response, TARGETS_DIRECTORY)
            else:
                print("Error:", response.text)
                with open("fails.csv", "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow([payload, response.text])
        except Exception as e:
            print("An error occurred:", e)
            with open("fails.csv", "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([payload, str(e)])


def save_response_to_directory(target, response, directory):
    for root, dirs, _ in os.walk(directory):
        for dir in dirs:
            if dir.startswith(target):
                with open(os.path.join(root, dir, "sessionData.json"), "w") as f:
                    json.dump(response.json(), f)


def get_targets_from_csv(csv_file_path):
    with open(csv_file_path, "r") as file:
        reader = csv.reader(file)
        targets = [row[0] for row in reader]
    return targets


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run targets against the app and filter the results"
    )
    parser.add_argument("--bountyId", help="Run targets against the app")
    parser.add_argument("--target", help="Single target to run against the app")
    parser.add_argument("--csv", help="CSV file containing targets")
    args = parser.parse_args()

    if args.target:
        targets = [args.target]
    elif args.csv:
        targets = get_targets_from_csv(args.csv)
    else:
        targets = get_targets(args.bountyId)

    post_to_app(targets)
