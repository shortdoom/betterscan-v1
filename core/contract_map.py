import re
import os
import json
import argparse
from web3 import Web3
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import pygraphviz as pgv
from networkx.drawing.nx_agraph import graphviz_layout

'''

python contract_map.py mainet:0x29d2bcf0d70f95ce16697e645e2b76d218d66109

'''

EXCEPTIONS = ["msg.value", "msg.sender", "new ", "this.", "address(", "abi."]
TYPE_EXCEPTIONS = ["uint", "int", "bool", "bytes", "string", "mapping"]
app_dir = os.path.dirname(os.path.realpath(__file__))
base_path = os.path.join(app_dir, "files", "out")


def check_if_source_exists(path):
    for root, dirs, _ in os.walk(base_path):
        for dir_name in dirs:
            if path in dir_name:
                session_data_path = os.path.join(root, dir_name, "sessionData.json")
                if os.path.isfile(session_data_path):
                    return session_data_path
                else:
                    print(f"sessionData.json not found in directory: {dir_name}")

    return None


def find_all_session_data_paths():
    dirs = os.listdir(base_path)
    session_data_paths = []
    for dir_name in dirs:

        if os.path.isfile(os.path.join(base_path, dir_name)):
            continue

        session_data_path = os.path.join(base_path, dir_name, "sessionData.json")
        if os.path.isfile(session_data_path):
            session_data_paths.append(session_data_path)
        else:
            print("Err")
            print(f"sessionData.json not found in directory: {dir_name}")

    return session_data_paths


def load_source(file_path):
    """
    Loads the JSON data from a file.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def get_session_data(session_data_path):
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
    - variable_type
    - variable_body
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

'''

Doesn't require an argument. Operates on files/out directory contents.
Use ContractMap to generate external_addresses, _calls (and other) data for ContractMapScan to use.

'''

class ContractMapScan:
    def __init__(self):
        self.session_data_paths = find_all_session_data_paths()
        self.session_external_addresses = []
        self.session_external_addresses_paths = {}
        self.contract_interactions = defaultdict(list)
        self.graph = nx.DiGraph()
        self.session_details = {}

    # Scans all of the files/out for external calls to the same addresses
    # NOTE: assumption is that files/out has relevant sessionData.json files
    def get_common_external_protocol(self):
        external_addresses_found = []
        for session_data_path in self.session_data_paths:
            session_data = get_session_data(session_data_path)
            external_addresses_found.append(
                session_data["contract_data"]["external_addresses"]
            )
        for addresses in external_addresses_found:
            for name, address in addresses.items():
                session_found = check_if_source_exists(address)
                if session_found:
                    self.contract_interactions[f"{name}:{address}"].setdefault(
                        name, session_found
                    )

    # Scans only specific directory
    def get_common_external_target(self, target_address):
        session_data_path = check_if_source_exists(target_address)
        external_addresses_paths = {}
        if session_data_path:
            session_data = get_session_data(session_data_path)
            external_addresses = session_data["contract_data"]["external_addresses"]
            for name, address in external_addresses.items():
                session_found = check_if_source_exists(address)
                if session_found:
                    external_addresses_paths[name] = session_found

            self.session_external_addresses_paths = external_addresses_paths

    def gen_protocol_graph(self):
        for path in self.session_data_paths:
            session_data = load_source(path)
            target_address = session_data.get("network_info", {}).get(
                "contract_address", ""
            )
            target_contract = session_data.get("network_info", {}).get(
                "contract_name", ""
            )
            target_address_external_calls = session_data.get("contract_data", {}).get(
                "external_addresses", {}
            )
            
            # TODO: Grab external_address path to sessionData.json, add to graph to use jump-to-session
            
            # TODO: Grab external_calls (expression) for target_address to use in graph
            
            self.graph.add_node(
                target_address, label=target_contract, address=target_address
            )

            for (
                external_contract_name,
                external_address,
            ) in target_address_external_calls.items():
                self.graph.add_node(
                    external_address,
                    label=external_contract_name,
                    address=external_address,
                )
                self.graph.add_edge(target_address, external_address)

                if external_address not in self.session_details:
                    self.session_details[external_address] = path

    def visualize_graph(self):
        A = nx.nx_agraph.to_agraph(self.graph)

        A.graph_attr.update(
            {
                "splines": "spline",
                "rankdir": "LR",
                "nodesep": "0.75",
                "ranksep": "1.2",
            }
        )

        A.layout("fdp")

        graph_path = os.path.join(base_path, "network_graph.png")
        A.draw(graph_path)

        print("Graph has been saved as 'network_graph.png'")

    def run(self):
        self.gen_protocol_graph()
        self.visualize_graph()

'''

target_address: <network>:<address> string, will look for the sessionData.json in files/out directory
session_data: dict/json data structure (sessionData.json) object, for use with external classes

script should be used with already generated sessionData.json files, it will not download contracts (TODO)

returns: external_addresses, external_calls as part of sessionData object

'''

class ContractMap:
    def __init__(self, target_address: str = None, session_data: dict = None):

        self.w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))

        if target_address:
            session_data_path = check_if_source_exists(target_address)
            # TODO: if/else to download the contract if sessionData.json not found (and run analyze.py)
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
            self.session_data = get_session_data(session_data_path)
            self.variable_call, self.abi_variable = generate_address_abi(
                self.session_data["variables_data"]
            )
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(target_address.split(":")[1]),
                abi=self.abi_variable,
            )
        else:
            # TODO: if/else to download the contract if sessionData.json not found (and run analyze.py)
            raise ValueError(
                "Session data not found and/or target address missing. Run the analytics first."
            )

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
    # contract_map = ContractMap(args.target_address)
    # contract_map.run_map()
    contract_map_scan = ContractMapScan()
    contract_map_scan.run()
    # contract_map_scan.get_common_external_protocol()
    # print("Contract interactions:", contract_map_scan.contract_interactions)
    # contract_map_scan.get_common_external_target(args.target_address)
