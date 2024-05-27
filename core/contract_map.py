import re
import os
import json
import argparse
from web3 import Web3
from downloader import DownloaderClass
from slither.slither import Slither
from slither.core.declarations import Function
from slither.core.declarations import Contract


EXCEPTIONS = ["msg.value", "msg.sender", "new ", "this.", "address(", "abi."]
TYPE_EXCEPTIONS = ["uint", "int", "bool", "bytes", "string", "mapping"]
app_dir = os.path.dirname(os.path.realpath(__file__))


def check_if_source_exists(path):
    base_path = os.path.join(app_dir, "files", "out")
    for root, dirs, _ in os.walk(base_path):
        for dir_name in dirs:
            if path in dir_name:
                session_data_path = os.path.join(root, dir_name, "sessionData.json")
                if os.path.isfile(session_data_path):
                    return session_data_path
                else:
                    print(f"sessionData.json not found in directory: {dir_name}")

    return None


def load_source(file_path):
    """
    Loads the JSON data from a file.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def _get_session_data(session_data_path):
    """
    Returns the session data from files/out/$network:address if it exists, otherwise returns None.
    """
    if session_data_path:
        data = load_source(session_data_path)
        return data
    return None


def generate_abi(variables_data):
    """
    Generates minimal ABI from the provided variables data.
    Each entry in the variables_data should have at least the following fields:
    - variable_name
    - variable_selector
    - variable_type
    This function filters out variables based on TYPE_EXCEPTIONS.
    """
    abi = []
    for var in variables_data:
        if var['is_variable'] and not any(var["variable_type"].startswith(_type) for _type in TYPE_EXCEPTIONS):
            abi.append({
                "constant": True,
                "inputs": [],
                "name": var["variable_name"],
                "outputs": [{"name": "", "type": "address"}],  # Assuming all are address type
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            })
    return abi


# AnalyticClass (with session_data), cli or other python scripts (with target_address)
# NOTE: This function is best initialized with a target_address from Downloader and sessionData from AnalyticClass
# NOTE: This should be initialized by app.py with full sessionData, not analyze.py with partial data
# NOTE: If user wants to generate map without an UI, use a targets_run.py script (requires re-working it into cli module fully)
# NOTE: targets_run.py will invoke ContractMap with appropriate argumetns


class ContractMap:
    def __init__(self, target_address: str = None):
        self.w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
        session_data_path = check_if_source_exists(target_address)

        if session_data_path:
            self.session_data = _get_session_data(session_data_path)
            self.abi = generate_abi(self.session_data["variables_data"])
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(target_address.split(":")[1]),
                abi=self.abi,
            )
        else:
            raise ValueError("Session data not found. Please run the downloader first.")

        self.target_address = (
            Web3.to_checksum_address(target_address.split(":")[1])
            if target_address
            else None
        )
        self.external_addresses = None

    def fetch_variable_addresses(self):
        results = {}
        for func_info in self.abi:
            func_name = func_info["name"]
            try:
                result = self.contract.functions[func_name]().call()
                results[func_name] = result
                print(f"Function {func_name} returned {result}")
            except Exception as e:
                print(f"Error calling function {func_name}: {e}")

        self.external_addresses = results
        print("External addresses:", self.external_addresses)
        
    def get_only_external_calls(self):
        lib_names = self.extract_lib_names(self.session_data["all_library_calls"])
        full_exclusions = lib_names.union(EXCEPTIONS)
        self.external_calls = [
            call
            for call in self.session_data["all_external_calls"]
            if not self.contains_exclusions(call, full_exclusions)
        ]

    def extract_lib_names(self, library_calls):
        pattern = re.compile(r"^(\w+)")
        lib_names = set()
        for call in library_calls:
            match = pattern.match(call)
            if match:
                lib_names.add(match.group(1))
        return lib_names

    def contains_exclusions(self, call, exclusions):
        for exclusion in exclusions:
            if exclusion in call:
                return True
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process external smart contracts."
    )
    parser.add_argument(
        "target_address", help="Target network:address string (e.g., 'mainet:0x')"
    )

    # parser.add_argument(
    #     "session_data", help="Session data JSON file (e.g., 'session_data.json')"
    # )

    args = parser.parse_args()
    contract_map = ContractMap(args.target_address)
    contract_map.fetch_variable_addresses()
