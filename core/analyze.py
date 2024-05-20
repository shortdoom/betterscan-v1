import logging
import subprocess
import argparse
import json
import os
import re

from slither.slither import Slither
from slither.slithir.operations import LowLevelCall

from slither.core.declarations import Function
from slither.core.variables.state_variable import StateVariable
from slither.core.declarations import Contract

from slither.printers.summary.constructor_calls import _get_source_code
from slither.tools.possible_paths.possible_paths import find_target_paths
from slither.utils.function import get_function_id

from utils.utils import get_detectors, get_slitherin_detectors, run_all_detectors

from prompt import PromptClass
from property_match import PropertyMatchClass
from contract_map import ContractMap

""" 
python analyze.py files/out/mainet:0x1337/your_target_dir/TargetContract.sol --target_name TargetContractName  --config_dir files/out/mainet:0x1337

target_compile: path to the solidity file that's a target of AnalyticsClass
taret_name: name of the contract in the solidity file to analyze (NOT the *.sol filename)
config_dir: path to the directory containing the crytic.config.json file, no need to specify if not using cryticCompile

returns *_sessionData.json file in the files/out directory

best to use full path for all arguments 
"""


class AnalyticsClass:
    def __init__(self, target_compile: str, target_name: str, config_dir: str = None):
        self.name = target_name

        if config_dir:
            config_dir = os.path.join(config_dir, "slither.config.json")
            with open(config_dir, "r") as config_file:
                solc_args_content = config_file.read()
                config = json.loads(solc_args_content)
        else:
            config = {}

        try:
            self.slither = Slither(target_compile, **config)
            print("Slither (AnalyticsClass.init) initialized successfully!")
        except Exception as e:
            print("Error initializing Slither (AnalyticsClass.init):", e)
            raise e

        self.property_check = PropertyMatchClass(self.slither)
        self.root_contract = None
        self.root_contract_path = None
        self.output_variables = []
        self.output_functions = []
        self.output_contract = {}
        self.output_sources = {}
        self.output_scan = []
        self.output_full = {}

    def get_prompts(self, function_data: dict, prompter: PromptClass):
        return prompter.construct_function_prompt(function_data)

    def get_mutability(self, function: Function):
        if function.visibility in ["external", "public"]:
            if function.view or function.pure:
                # public view / pure - no external state change possible
                return 3
            else:
                # public state write in body || public non-view w/ external state change possible
                return 1
        else:
            # internal / private state changing (internal are probably used in group 1)
            return 2

    def get_basic_properties(self, function: Function):
        return self.property_check.run_property_check(function)

    def get_internal_functions(self, function: Function):
        # 1st order internal_calls
        internal_calls_root = [
            self.root_contract.get_function_from_full_name(x.full_name)
            for x in function.internal_calls
        ]

        # 2nd order internal calls (internal calls of internal calls)
        internal_calls_sub = [
            self.root_contract.get_function_from_full_name(sub_func.full_name)
            for func in internal_calls_root
            if func is not None
            for sub_func in func.internal_calls
            if sub_func is not None
        ]

        all_internal_calls = internal_calls_root + internal_calls_sub

        # Remove duplicates
        all_internal_calls = list(
            {
                func.full_name: func for func in all_internal_calls if func is not None
            }.values()
        )

        # Returns all internal calls tree NOTE: can overshoot
        return "\n\n".join(
            _get_source_code(x).lstrip() for x in all_internal_calls if x
        )

    def get_modifier_functions(self, function: Function):
        modifier_calls = [
            self.root_contract.get_function_from_full_name(x.full_name)
            for x in function.modifiers
        ]
        return [_get_source_code(x) for x in modifier_calls if x]

    def get_low_level_calls(self, function: Function) -> bool:
        nodes = function.nodes
        for n in nodes:
            if any(isinstance(ir, LowLevelCall) for ir in n.irs):
                return True
        return False

    # endregion
    ###################################################################################
    ###################################################################################

    def analyze_variable(self, variable: StateVariable):
        data = {
            "is_variable": True,
            "contract_name": variable.contract.name,
            "variable_name": variable.name,
            "variable_selector": str(hex(get_function_id(variable.full_name))),
            "variable_full_name": variable.full_name,
            "variable_canonical_name": variable.canonical_name,
            "variable_body": variable.source_mapping.content,
            "variable_type": (
                variable.source_mapping.content.split()[0]
                if not variable._type.is_dynamic
                else "mapping"
            ),
            "variable_is_dynamic": variable._type.is_dynamic,
            "variable_initialized": variable._initialized,
            "variable_visibility": variable._visibility,
            "variable_is_constant": variable._is_constant,
            "variable_is_immutable": variable._is_immutable,
            "line_numbers": [
                variable.source_mapping.lines[0],
                variable.source_mapping.lines[-1],
            ],
        }
        self.output_variables.append(data)

    def analyze_function(self, function: Function, inherited=False):
        summary = function.get_summary()
        paths = find_target_paths(self.slither, [function])

        data = {
            "contract_name": summary[0],
            "contract_inherited": inherited,
            "function_full_name": summary[1],
            "function_selector": str(hex(get_function_id(function.full_name))),
            "function_signature_str": function.signature_str,
            "function_parameters": [param.name for param in function.parameters],
            "function_returns": [param.name for param in function.returns],
            "function_canonical_name": function.canonical_name,
            "visibility": summary[2],
            "modifiers": summary[3],
            "state_vars_read": summary[4],
            "state_vars_written": summary[5],
            "internal_calls": [func.full_name for func in function.internal_calls],
            "external_calls": summary[7],
            "external_calls_functions": [
                call[1].full_name
                for call in function.high_level_calls
                if isinstance(call[1], Function)
            ],  # required for preprocess_all_reachable_from
            "cyclomatic_complexity": summary[8],
            "function_body": _get_source_code(function).lstrip(),
            "line_numbers": [
                function.source_mapping.lines[0],
                function.source_mapping.lines[-1],
            ],
            "modifiers_body": (
                [_get_source_code(x) for x in function.modifiers]
                if function.modifiers
                else []
            ),
            "priority": self.get_mutability(function),
            "internal_functions": self.get_internal_functions(function) or [],
            "external_functions_body": [],
            "basic_codes": self.get_basic_properties(function),
            "all_reachable_from_functions": [
                func.full_name for func in function.all_reachable_from_functions
            ],
            "is_implemented": function.is_implemented,
            "is_empty": function.is_empty,
            "variables": [var.name for var in function.variables],
            "contains_asm": function.contains_assembly,
            "expressions": [var.source_mapping.content for var in function.expressions],
            "is_shadowed": function.is_shadowed,
            "shadows": function.shadows,
            "function_type": function.function_type.value,
            "is_protected": function._is_protected,
            "has_documentation": function.has_documentation,
            "low_level_calls": self.get_low_level_calls(function),
            "solidity_calls": [var.name for var in function._solidity_calls],
            "high_level_calls": [
                func_or_var.name for _, func_or_var in function.high_level_calls
            ],
            "library_level_calls": [
                func_or_var.name for _, func_or_var in function.library_calls
            ],
            "all_conditional_state_variables_read": [
                var.full_name for var in function.all_conditional_state_variables_read()
            ],
            "all_conditional_solidity_variables_read": [
                var.name for var in function.all_conditional_solidity_variables_read()
            ],
            "all_solidity_variables_used_as_args": [
                var.name for var in function.all_solidity_variables_used_as_args()
            ],
            "all_paths_to_function": [func.full_name for tup in paths for func in tup],
        }

        self.output_functions.append(data)

        return data

    def analyze_contract(self, contract: Contract):
        data = {
            "contract_name": contract.name,
            "immediate_inheritance": [
                parent.name for parent in contract.immediate_inheritance
            ],
            "is_upgradeable": contract.is_upgradeable,
            "contract_lines": [
                contract.source_mapping.lines[0],
                contract.source_mapping.lines[-1],
            ],
            "structures": [struct.name for struct in contract.structures],
            "structures_types": [
                variable.source_mapping.content
                for struct in contract.structures
                for variable in struct.elems_ordered
            ],
            "structures_elements": [
                variable.solidity_signature
                for struct in contract.structures
                for variable in struct.elems_ordered
            ],
            "structures_with_elements": [
                f"{struct.name}.{variable.solidity_signature}"
                for struct in contract.structures
                for variable in struct.elems_ordered
            ],
            "all_variables": [var.name for var in contract.state_variables],
            "all_function_names": [func.full_name for func in contract.functions],
            "all_library_calls": list(set([
                call[1].canonical_name
                for call in contract.all_library_calls
                if isinstance(call[1], Function)
            ])),
            "all_solidity_calls": list(set([
                call.name for func in contract.functions for call in func.solidity_calls
            ])),
            "all_external_calls": list(set([
                str(call)
                for func in contract.functions
                for call in func.external_calls_as_expressions
            ])),
            "all_reachable_from_functions": list(
                set(
                    [
                        call.full_name
                        for func in contract.functions
                        for call in func.all_reachable_from_functions
                    ]
                )
            ),
            "enums": [enum.name for enum in contract.enums],
            "events": [event.name for event in contract.events],
            "custom_errors": [err.name for err in contract.custom_errors],
            "fallback_function": bool(contract.fallback_function),
            "receive_function": bool(contract.receive_function),
            "ercs": contract.ercs(),
        }

        self.output_contract = data
        
        contract_map = ContractMap(None, data)
        contract_map.get_only_external_calls()
        data["external_calls_to_variables"] = contract_map.external_calls

        return data

    def run_slither_scan(self):
        detectors = get_detectors()
        slitherin_detectors = get_slitherin_detectors()
        all_detectors = list(set(detectors + slitherin_detectors))
        _, results_detectors, _ = run_all_detectors(self.slither, all_detectors)

        def extract_contract_signature_and_nodes(elements):
            nodes = []
            contract_signature_info = {}

            for element in elements:
                if element["type"] == "function":
                    type_specific_fields = element.get("type_specific_fields", {})
                    parent = type_specific_fields.get("parent", {})
                    if "name" in parent and "signature" in type_specific_fields:
                        source_mapping = element.get("source_mapping", {})
                        filename_absolute = source_mapping.get("filename_absolute", "")
                        lines = source_mapping.get("lines", [])
                        if filename_absolute and lines:
                            path = f"{filename_absolute}#{lines[0]}-{lines[-1]}"
                        else:
                            path = ""

                        contract_signature_info = {
                            "contract": parent["name"],
                            "full_name": type_specific_fields["signature"],
                            "path": path,
                        }

                elif element["type"] == "node":
                    nodes.append(element["name"])

            if nodes:
                contract_signature_info["expressions"] = nodes

            return contract_signature_info

        def clean_description(description):
            cleaned_description = re.sub(r"\s*\([^)]*\)", "", description)
            return cleaned_description

        simplified_results = []
        for result in results_detectors:
            elements = result.get("elements", [])
            contract_signature_and_nodes = extract_contract_signature_and_nodes(
                elements
            )
            cleaned_description = clean_description(result["description"])

            simplified_result = {
                "description": cleaned_description,
                "check": result["check"],
                "impact": result["impact"],
                "confidence": result["confidence"],
                **contract_signature_and_nodes,  # Merge in the contract, signature, and nodes information
            }
            simplified_results.append(simplified_result)

        self.output_scan.extend(simplified_results)

    def run_semgrep_scan(self, path_to_scan, config="p/smart-contracts"):
        try:
            command = ["semgrep", "--config", config, "--json", path_to_scan]
            result = subprocess.run(command, capture_output=True, text=True, check=True)

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

                self.output_scan.extend(simplified_results)

        except subprocess.CalledProcessError as e:
            print(f"Semgrep scan failed with error: {e}")
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON output from Semgrep: {e}")

    def run_ityfuzz_scan():
        pass

    def analyze_external(self, contract: Contract):
        pass

    def run_analysis(self):
        for contract in self.slither.contracts:

            path_to_source = contract.source_mapping.filename.absolute
            with open(
                path_to_source, encoding="utf8", newline="", errors="replace"
            ) as source_file:
                source_code = source_file.read()
            self.output_sources[contract.name] = {
                "path": path_to_source,
                "source_code": source_code,
            }

            # TODO: Currently it parses only root contract deployed at the address
            if contract.name == self.name:
                self.root_contract = contract
                self.root_contract_path = path_to_source
                self.property_check.set_root_contract(contract)

                # contract Test is A,B,C - sometimes A,B,C may be main entry points
                contracts_inherited = [
                    parent
                    for parent in contract.immediate_inheritance
                    if not parent.is_interface
                ]

                for inherited in contracts_inherited:
                    for function in inherited.functions:
                        if function.contract_declarer.is_interface:
                            continue
                        if (
                            function.full_name
                            != "slitherConstructorConstantVariables()"
                            and function.full_name != "slitherConstructorVariables()"
                        ):
                            self.analyze_function(function, True)

                # main contract functions
                functions_declared = [
                    function for function in contract.functions_declared
                ]

                for function in contract.functions:
                    if (
                        function.full_name != "slitherConstructorConstantVariables()"
                        and function.full_name != "slitherConstructorVariables()"
                    ):
                        if function in functions_declared:
                            self.analyze_function(function)

                print("Functions analyzed for contract:", contract.name)

                for variable in contract.state_variables:
                    self.analyze_variable(variable)

                self.analyze_contract(contract)
                self.analyze_external(contract)

        try:
            self.run_slither_scan()
        except Exception as e:
            logging.error(f"Slither detection failed: {e}", exc_info=True)

        try:
            self.run_semgrep_scan(self.root_contract_path)
        except Exception as e:
            logging.error(f"Semgrep detection failed: {e}", exc_info=True)

        self.output_full = {
            "contract_data": self.output_contract,
            "functions_data": self.output_functions,
            "variables_data": self.output_variables,
            "source_code": self.output_sources,
            "scan_results": self.output_scan,
        }

        # TODO: Call ContractMap class here with external_calls_functions
        # NOTE: Step 1) Just make a call lol. construct abi, filter out lib funcs
        # NOTE: Step 2) use the return address to re-init DownloadClass

        return self.output_full

    def load_target_contract(self, target_name: str):
        for contract in self.slither.contracts:
            if contract.name == target_name:
                return contract

    def load_target_function(self, target_name: str):
        for contract in self.slither.contracts:
            for function in contract.functions:
                if function.name == target_name:
                    return function


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Parse functions in Solidity contracts"
    )

    parser.add_argument(
        "target_compile",
        help="Target path to directory or cryticCompile object for slither",
    )
    parser.add_argument(
        "target_name",
        default="",
        help="Target contract name for analysis (not filename)",
    )
    parser.add_argument(
        "config_dir",
        default="",
        help="Path to the directory containing the config file for solc, changes cwd(), only for cryticCompile",
    )

    args = parser.parse_args()

    # NOTE: Move to the directory where .config.json file is located, otherwise Slither/Crytic won't compile
    if args.config_dir:
        os.chdir(args.config_dir)

    analyzer = AnalyticsClass(
        args.target_compile,
        args.target_name,
        args.config_dir,
    )
    prompter = PromptClass()
    prompter.load_prompt_strategy("open_ended_0.1_unguided")
    data = analyzer.run_analysis()

    script_dir = os.path.dirname(os.path.realpath(__file__))
    name = args.target_name + "_sessionData.json"
    file_path = os.path.join(script_dir, "files/out", name)

    with open(file_path, "w") as f:
        json.dump(analyzer.output_full, f, indent=4)
