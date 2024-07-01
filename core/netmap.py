import re
import os
import json
import argparse
from web3 import Web3
import networkx as nx
from runner import run_external_targets, run_analysis
from utils.data import (
    check_if_source_exists,
    find_all_session_data_paths,
    get_session_data,
    load_source,
)

"""

python netmap.py mainet:0x29d2bcf0d70f95ce16697e645e2b76d218d66109

"""

EXCEPTIONS = ["msg.value", "msg.sender", "new ", "this.", "address(", "abi."]
TYPE_EXCEPTIONS = ["uint", "int", "bool", "bytes", "string", "mapping"]
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
app_dir = os.path.dirname(os.path.realpath(__file__))
base_path = os.path.join(app_dir, "files", "out")


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


"""

Use ContractMap to generate external_addresses, _calls (and other) data for ContractMapScan to use.
Running ContractMapScan requires data fields in sessionData.json from ContractMap.

crawl_level: int, number of levels to crawl external calls sources
    - default: None, crawl only target address
    - 1: crawl 1st level of calls (e.g, state var addresses of target address)
    - 0: crawl all levels of calls (e.g., state var addresses of target address and their state var addresses)
    
"""


class ContractMapScan:
    def __init__(self, crawl_level=None):
        self.session_data_paths = find_all_session_data_paths()
        self.session_external_addresses = []
        self.session_external_addresses_paths = {}
        self.graph = nx.DiGraph()
        self.crawl_level = crawl_level

        if crawl_level is not None:
            self.crawl_level = int(crawl_level)
        else:
            self.crawl_level = None

    def get_external_sources(self):
        external_addresses_found = []
        for session_data_path in self.session_data_paths:
            session_data = get_session_data(session_data_path)
            external_addresses_found.append(
                session_data["contract_data"]["external_addresses"]
            )

        for addresses in external_addresses_found:

            for name, address in addresses.items():
                session_found = check_if_source_exists(address)
                if not session_found:

                    network = session_data["network_info"]["contract_network"]
                    external_target = f"{network}:{address}"

                    if address != ZERO_ADDRESS:
                        if self.crawl_level != 1:
                            try:
                                run_analysis(external_target, self.crawl_level)
                            except Exception as e:
                                print(
                                    "Error: get_external_sources.run_analysis(external_target):",
                                    e,
                                )
                                continue
                        else:
                            try:
                                run_external_targets(external_target)
                            except Exception as e:
                                print(
                                    "Error: get_external_sources.run_external_targets(external_target)"
                                )
                                continue
                    else:
                        print("ZERO_ADDRESS not supported")
                        continue

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

            target_external_calls_exp = session_data.get("contract_data", {}).get(
                "external_calls", []
            )

            # NOTE: Grab external_address path to sessionData.json, add to graph to use jump-to-session
            target_external_session_path = session_data.get("network_info", {}).get(
                "data_directory", ""
            )

            # NOTE: Grab external_calls (expression) for target_address to use in graph
            expressions = [
                call
                for call in target_external_calls_exp
                if any(key in call for key in target_address_external_calls.keys())
            ]

            self.graph.add_node(
                target_address,
                label=(
                    target_contract
                    if target_address != ZERO_ADDRESS
                    else "ZERO_ADDRESS"
                ),
                address=target_address,
                session_path=(
                    target_external_session_path
                    if target_address != ZERO_ADDRESS
                    else ""
                ),
                ext_expressions=expressions,
            )

            for (
                external_contract_name,
                external_address,
            ) in target_address_external_calls.items():
                self.graph.add_node(
                    external_address,
                    label=(
                        external_contract_name
                        if external_address != ZERO_ADDRESS
                        else "ZERO_ADDRESS"
                    ),
                    address=external_address,
                )
                self.graph.add_edge(target_address, external_address)

    def analyze_protocol_graph(self):
        for node in self.graph.nodes:
            print(node)
            print(self.graph.nodes[node])


"""
Used to map what external addresses are being called by the target_address

target_address: <network>:<address> string, will look for the sessionData.json in files/out directory
session_data: dict/json data structure (sessionData.json) object, for use with external classes

script should be used with already generated sessionData.json files, it will not download contracts (TODO)

returns: external_addresses, external_calls as a part of the sessionData object

"""


class ContractMap:
    def __init__(self, target_address: str = None, session_data: dict = None):

        # TODO: Add support for CONFIG file
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
    # contract_map_scan.get_external_sources()
    # print("Contract interactions:", contract_map_scan.contract_interactions)
    # contract_map_scan.get_common_external_target(args.target_address)
