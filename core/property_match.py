from typing import List
from slither.core.declarations import Function
from slither.core.declarations import Contract

from slither.printers.summary.constructor_calls import _get_source_code

class PropertyMatchClass:
    def __init__(self, slither):
        self.slither = slither
        self.root_contract = None
        self.prompt_codes = []

    def set_root_contract(self, contract: Contract):
        self.root_contract = contract

    def run_property_check(self, function: Function) -> List[int]:
        return (
            self.is_eth_function(function)
            + self.is_eip20_function(function)
            + self.is_uniswap_function(function)
            + self.is_low_level_call(function)
        )

    def is_eth_function(self, function: Function) -> List[int]:
        eth_scenario = []
        function_body = _get_source_code(function)
        # contract._fallback_function and _receive_function
        if self.root_contract.fallback_function:
            eth_scenario.append(0)
        if self.root_contract.receive_function:
            eth_scenario.append(1)
        # function.payable and function.can_send_eth
        if function._payable:
            eth_scenario.append(2)
        if function._can_send_eth:
            eth_scenario.append(3)
        # also, address(this).balance, msg.value, address.transfer, address.send
        keywords = ["address(this).balance", "msg.value"]
        if any(keyword in function_body for keyword in keywords):
            eth_scenario.append(4)
        return eth_scenario

    def is_eip20_function(self, function: Function) -> List[int]:
        eth_scenario = []
        function_body = _get_source_code(function)

        # contract is ERC20
        transfer = self.root_contract.get_function_from_signature(
            "transfer(address,uint256)"
        )
        transfer_from = self.root_contract.get_function_from_signature(
            "transferFrom(address,address,uint256)"
        )
        approve = self.root_contract.get_function_from_signature(
            "approve(address,uint256)"
        )

        if transfer and transfer_from and approve is not None:
            eth_scenario.append(5)

        # function uses ERC20 interface
        eip20_functions = ["transfer", "approve", "transferFrom"]
        if any(keyword in function_body for keyword in eip20_functions):
            eth_scenario.append(6)

        return eth_scenario

    def is_uniswap_function(self, function: Function) -> List[int]:
        eth_scenario = []
        function_body = _get_source_code(function)
        uniswap_functions = ["swapExactETHForTokens", "swapExactTokensForETH"]
        # calls uniswap-like contracts (interface implemented)
        if any(keyword in function_body for keyword in uniswap_functions):
            eth_scenario.append(7)

        return eth_scenario

    def is_low_level_call(self, function: Function) -> List[int]:
        eth_scenario = []
        # delegatecall catch
        if function.low_level_calls:
            eth_scenario.append(8)
        return eth_scenario

    def is_signature_used(self, function: Function) -> List[int]:
        eth_scenario = []
        function_body = _get_source_code(function)
        # signature check
        if "ecrecover" in function_body:
            eth_scenario.append(9)
        return eth_scenario
