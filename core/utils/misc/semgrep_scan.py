import argparse
import subprocess
import json

'''

Run OSS semgrep rules for Solidity on the specified Solidity file through Python.

semgrep --config p/smart-contracts <full-path-to-sol-file>
'''

def run_semgrep_scan(path_to_scan, config="p/smart-contracts"):
    try:
        # Run the Semgrep scan with the specified configuration and target path
        command = ["semgrep", "--config", config, "--json", path_to_scan]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Parse the JSON output from Semgrep
        if result.stdout:
            scan_results = json.loads(result.stdout)
            findings = scan_results.get("results", [])

            simplified_results = [
                {
                    "description": finding["extra"]["message"],
                    "check": finding["check_id"],
                    "impact": finding["extra"]["severity"],
                    "path": f"{finding['path']}#{finding['start']['line']}-{finding['end']['line']}",
                    "confidence": "",
                    "contract": "",
                }
                for finding in findings
            ]

            print(json.dumps(simplified_results, indent=4))

            return simplified_results
        return []

    except subprocess.CalledProcessError as e:
        print(f"Semgrep scan failed with error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON output from Semgrep: {e}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a semgrep scan.")
    parser.add_argument("path_to_scan", help="The path to scan.")
    parser.add_argument(
        "--config",
        default="p/smart-contracts",
        help="The semgrep configuration to use.",
    )
    args = parser.parse_args()

    run_semgrep_scan(args.path_to_scan, args.config)