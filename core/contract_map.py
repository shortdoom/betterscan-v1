import re
import argparse
from web3 import Web3
from downloader import DownloaderClass
from slither.slither import Slither
from slither.core.declarations import Function
from slither.core.declarations import Contract

w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))

EXCEPTIONS = ["msg.value", "msg.sender", "new ", "this.", "address(", "abi."]
TYPE_EXCEPTIONS = ["uint", "int", "bool", "bytes", "string", "mapping"]

# AnalyticClass (with session_data), cli or other python scripts (with target_string)
# NOTE: This function is best initialized with a target_string from Downloader and sessionData from AnalyticClass
# NOTE: This should be initialized by app.py with full sessionData, not analyze.py with partial data
# NOTE: If user wants to generate map without an UI, use a targets_run.py script (requires re-working it into cli module fully)
# NOTE: targets_run.py will invoke ContractMap with appropriate argumetns

class ContractMap:
    def __init__(self, target_string: str = None, session_data: list = None):
        self.session_data = session_data
        self.target_string = target_string
        self.external_calls = None
        self.external_interface = None
        self.external_addresses = None
        self.downloader_map = None
      
    def fetch_variable_addresses(self):
        """
        Fetches the addresses or data from the contract based on variable selectors
        that are not in TYPE_EXCEPTIONS.
        """
        results = {}
        for var in self.session_data:
            if not any(var["variable_type"].startswith(_type) for _type in TYPE_EXCEPTIONS):
                function_selector = var["variable_selector"]
                print("calling", function_selector, "with type", var["variable_type"])
                try:
                    call_data = function_selector
                    result = w3.eth.call({
                        'to': self.target_string, # TODO: ERR! Currently None
                        'data': call_data
                    })
                    results[var["variable_name"]] = result.hex()
                except Exception as e:
                    print(f"Error calling variable {var['variable_name']}: {e}")
        
        self.external_addresses = results
          

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
