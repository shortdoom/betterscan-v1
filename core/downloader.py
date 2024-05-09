from pathlib import Path
import os
import argparse
import shutil
import datetime
from crytic_compile import CryticCompile

"""
Wrapper around crytic-compile downloader
python downloader.py <network>:<address>
"""


class DownloaderClass:
    # target_string is <network>:<address>
    def __init__(self, target_string: str, api_key: str = None):

        # custom api-key for etherscan
        self.api_key = api_key
        self.api_keys = {
            "etherscan_api_key": self.api_key,
            "arbiscan_api_key": self.api_key,
            "polygonscan_api_key": self.api_key,
            "test_polygonscan_api_key": self.api_key,
            "avax_api_key": self.api_key,
            "ftmscan_api_key": self.api_key,
            "bscan_api_key": self.api_key,
            "optim_api_key": self.api_key,
            "base_api_key": self.api_key,
            "gno_api_key": self.api_key,
            "polyzk_api_key": self.api_key,
        }

        # absolute path to this file
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        
        # path where script runs
        self.working_dir = os.path.join(self.script_dir, "files/out")
        
        # name of the target contract
        self.root_contract = str()
        
        # {"ContractName": "", "Address": "", "Network": "", "LastChecked": ""}
        self.contract_info = dict()
        
        # absolute path of the self.root_contract contract file
        self.crytic_root_file = str()
        
        # crytic-compile access
        self.crytic_object = None

        # create directory <network>:<address> in the working_dir
        if ":" in target_string:
            self.target_name = target_string
            self.output_dir = Path(os.path.join(self.working_dir, self.target_name))
            os.makedirs(self.output_dir, exist_ok=True)
        else:
            self.target_name = "mainet:" + target_string
            self.output_dir = Path(os.path.join(self.working_dir, self.target_name))
            os.makedirs(self.output_dir, exist_ok=True)

    def get_source_code(self):
        os.chdir(self.output_dir)

        if self.api_key:
            try:
                self.crytic_object = CryticCompile(self.target_name, **self.api_keys)
                if self.crytic_object.bytecode_only:
                    raise Exception(
                        "Downloader.get_source_code(api_key) Error: Bytecode only accessible"
                    )
            except Exception as e:
                raise Exception(f"Downloader.get_source_code(api_key) Error: {e}")
        else:
            try:
                self.crytic_object = CryticCompile(self.target_name)
                if self.crytic_object.bytecode_only:
                    raise Exception(
                        "Downloader.get_source_code(api_key) Error: Bytecode only accessible"
                    )
            except Exception as e:
                raise Exception(f"Downloader.get_source_code() Error: {e}")

    def restructure_for_crytic_compile(self):

        crytic_path = self.output_dir / "crytic-export" / "etherscan-contracts"

        for contract_item in crytic_path.iterdir():

            if contract_item.name == "crytic_compile.config.json":
                continue

            try:

                ###############################################
                _, target_name_from_dir = contract_item.name.split("-", 1)

                if "-" in target_name_from_dir:
                    network, contract_name = target_name_from_dir.rsplit("-", 1)
                else:
                    network = "mainet"
                    contract_name = target_name_from_dir

                ###############################################
                single_dir_type = False

                if contract_item.is_file():
                    single_contract_name, _ = os.path.splitext(contract_name)
                    shutil.move(
                        str(contract_item),
                        str(self.output_dir / f"{contract_name}"),
                    )

                    # Move the crytic_compile.config.json too
                    json_file = contract_item.parent / "crytic_compile.config.json"
                    if json_file.exists():
                        shutil.move(
                            str(json_file),
                            str(self.output_dir),
                        )
                    single_dir_type = True
                else:
                    contract_items = list(contract_item.iterdir())
                    for item in contract_items:
                        shutil.move(str(item), str(self.output_dir))

            except Exception as e:
                raise Exception(f"Error processing {contract_item.name}: {e}")

        ################################################################

        contract_info = {
            "ContractName": single_contract_name if single_dir_type else contract_name,
            "Address": self.target_name.split(":")[1],
            "Network": network,
            "LastChecked": datetime.datetime.now().isoformat(),
            "Output_Dir": str(self.output_dir),
        }

        self.contract_info = contract_info

        shutil.rmtree(self.output_dir / "crytic-export")
        new_dir_name = f"{self.output_dir.parent}/{self.output_dir.name}:{single_contract_name if single_dir_type else contract_name}"
        os.rename(self.output_dir, new_dir_name)
        self.output_dir = Path(new_dir_name)
        self.root_contract = single_contract_name if single_dir_type else contract_name

        # Copy crytic_compile.config.json to slither.config.json
        shutil.copy(
            self.output_dir / "crytic_compile.config.json",
            self.output_dir / "slither.config.json",
        )

        # crytic_root_file is the absolute path of the target contract_name.sol file found in the current directory or its subdirectories
        try:
            for file_path in Path.cwd().rglob(
                f"{single_contract_name if single_dir_type else contract_name}.sol"
            ):
                self.crytic_root_file = str(file_path)
                break
        except Exception as e:
            raise Exception(
                f"File {contract_name}.sol not found in the current directory or its subdirectories: {e}"
            )

    def run_crytic(self):
        try:
            self.get_source_code()
            self.restructure_for_crytic_compile()
        except Exception as e:
            raise Exception(f"Error running run_crytic(): {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process smart contracts."
    )
    parser.add_argument(
        "target_string", help="Target network:address string (e.g., 'mainet:0x')"
    )
    
    parser.add_argument(
        "--api_key", help="API key for etherscan", default=None, nargs="?"
    )

    args = parser.parse_args()
    downloader = DownloaderClass(args.target_string, args.api_key)
    downloader.run_crytic()
