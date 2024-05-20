import re
import argparse
from web3 import Web3
from downloader import DownloaderClass
from slither.slither import Slither
from slither.core.declarations import Function
from slither.core.declarations import Contract

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

EXCEPTIONS = ["msg.value", "msg.sender", "new ", "this.", "address(", "abi."]

# AnalyticClass (with session_data), cli or other python scripts (with target_string)
class ContractMap:
    def __init__(self, target_string: str = None, session_data: list = None):
        self.session_data = session_data
        self.target_string = target_string
        self.external_calls = None
        self.external_interface = None
        self.external_addresses = None
        self.downloader_map = None

    def get_only_external_calls(self):
        lib_names = self.extract_lib_names(self.session_data["all_library_calls"])
        full_exclusions = lib_names.union(EXCEPTIONS)        
        self.external_calls = [call for call in self.session_data["all_external_calls"]
                               if not self.contains_exclusions(call, full_exclusions)]

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


    def get_external_interface(self):
        self.external_interface = list(
            set([re.match(r"(\w+)\.", call).group(1) for call in self.external_calls])
        )

    def call_external_interfaces(self):
        addresses = []

        for contract, function_name in zip(
            self.external_addresses, self.external_interfaces
        ):
            try:
                address = contract.functions[function_name].call()
                addresses.append(address)
            except Exception as e:
                print(f"Error calling function {function_name} on contract: {e}")

        self.external_addresses = addresses

    def map_external_interface(self):
        for address in self.external_addresses:
            try:
                self.downloader_map = DownloaderClass(f"{self.target_string}:{address}")
                self.downloader_map.run_crytic()
            except Exception as e:
                print(f"Error running DownloaderClass: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process external smart contracts."
    )
    parser.add_argument(
        "target_string", help="Target network:address string (e.g., 'mainet:0x')"
    )

    args = parser.parse_args()
    contract_map = ContractMap(args.target_string)
