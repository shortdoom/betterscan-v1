import re
import os
import json
import argparse
from web3 import Web3

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


def generate_address_abi(variables_data):
    """
    Generates minimal ABI from the provided variables data.
    Each entry in the variables_data should have at least the following fields:
    - variable_name
    - variable_selector
    - variable_type
    This function filters out variables based on TYPE_EXCEPTIONS.
    """
    abi = []
    variable_call = {}
    for var in variables_data:
        if var["is_variable"] and not any(
            var["variable_type"].startswith(_type) for _type in TYPE_EXCEPTIONS
        ):

            # address constant T = 0x1234567890123456789012345678901234567890;
            if "variable_body" in var:
                match = re.search(r"0x[a-fA-F0-9]{40}", var["variable_body"])
                if match:
                    variable_call[var["variable_name"]] = match.group()
                    continue

            abi.append(
                {
                    "constant": True,
                    "inputs": [],
                    "name": var["variable_name"],
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            )

    return variable_call, abi


class ContractMap:
    def __init__(self, target_address: str = None, session_data: dict = None):

        self.w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
        
        if target_address:        
            session_data_path = check_if_source_exists(target_address)
            self.target_address = (
            Web3.to_checksum_address(target_address.split(":")[1])
            if target_address
            else None
        )

        if session_data:
            self.session_data = session_data
            self.variable_call, self.abi_variable = generate_address_abi(
                self.session_data["variables_data"]
            )
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(target_address.split(":")[1]),
                abi=self.abi_variable,
            )
        elif session_data_path:
            self.session_data = _get_session_data(session_data_path)
            self.variable_call, self.abi_variable = generate_address_abi(
                self.session_data["variables_data"]
            )
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(target_address.split(":")[1]),
                abi=self.abi_variable,
            )
        else:
            # TODO: Add main.py (similar to app.py) that'll generate the sessionData.json
            raise ValueError("Session data not found and/or target address missing. Run the analytics first.")


        self.external_addresses = None
        self.external_calls = None
        
    def run_map(self):
        
        if not self.target_address:
            raise ValueError("Target address not provided.")
        
        if not self.session_data:
            raise ValueError("Session data not found.")
        
        try:
            self.resolve_variable_to_address()
            self.get_only_external_calls()
            print("External addresses:", self.external_addresses)
            print("External calls:", self.external_calls)
        except Exception as e:
            print(f"Error: {e}")
        
    def resolve_variable_to_address(self):
        results = {}
        for func_info in self.abi_variable:
            func_name = func_info["name"]
            try:
                result = self.contract.functions[func_name]().call()
                results[func_name] = result
            except Exception as e:
                print(f"Error calling function {func_name}: {e}")

        results.update(self.variable_call)
        self.external_addresses = results

    def get_only_external_calls(self):
        contract_data = self.session_data["contract_data"]
        lib_names = self.extract_lib_names(contract_data["all_library_calls"])
        full_exclusions = lib_names.union(EXCEPTIONS)
        self.external_calls = [
            call
            for call in contract_data["all_external_calls"]
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

    args = parser.parse_args()
    contract_map = ContractMap(args.target_address)
    contract_map.run_map()
