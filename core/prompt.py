from typing import List
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

class PromptClass:
    def __init__(self):
        self.prompt_strategy = str
        self.prompt_template = str
        self.extra_data = str
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.prompts_file = os.path.join(self.script_dir, "files/prompts/prompts.json")

    def get_all_prompt_strategies(self):
        try:
            # Load the prompt strategies from the JSON file using the absolute path
            with open(self.prompts_file, "r") as f:
                prompt_strategies = json.load(f)

            return [strategy["name"] for strategy in prompt_strategies]

        except Exception as e:
            print(f"Error loading prompt strategies: {e}")
            return None

    def load_prompt_strategy(self, prompt_strategy: str):
        try:
            # Load the prompt strategies from the JSON file using the absolute path
            with open(self.prompts_file, "r") as f:
                prompt_strategies = json.load(f)

            # Find the strategy with the given name
            strategy = next(
                (s for s in prompt_strategies if s["name"] == prompt_strategy), None
            )

            if strategy is None:
                print(f"No strategy found with name: {prompt_strategy}")
                return

            # Set the template_name and extra_data attributes based on the loaded strategy
            self.prompt_strategy = prompt_strategy
            self.prompt_template = strategy["prompt_template"]
            self.extra_data = strategy["extra_data"]

        except Exception as e:
            print(f"Error loading prompt strategy: {e}")

    def construct_function_prompt(self, function_data: dict):
        try:
            internal_functions_data = function_data.get("internal_functions", [])
            if isinstance(internal_functions_data, str):
                internal_functions = internal_functions_data
            else:
                internal_functions = "\n".join(internal_functions_data)

            external_functions_data = function_data.get("external_functions", [])
            if isinstance(external_functions_data, str):
                external_functions = external_functions_data
            else:
                external_functions = "\n".join(external_functions_data)

            function_body = function_data.get("function_body", "")

            extra_data = [
                f"{key}:{value}"
                for item in self.extra_data
                for key, value in item.items()
            ]

            return (
                self.prompt_template.replace("$MAIN_FUNCTION", function_body)
                .replace("$INTERNAL_FUNCTIONS", internal_functions)
                .replace("$EXTERNAL_FUNCTIONS", external_functions)
                .replace("$INDEX:$PROMPT", "\n".join(extra_data))
            )
        except Exception as e:
            print("Error in construct_function_prompt:", e)
            return "Error constructing prompt"
