from flask import Flask, jsonify, request, render_template
import numpy as np
from analyze import AnalyticsClass
from analyze import PromptClass
from downloader import DownloaderClass
from netmap import ContractMap
from netmap import ContractMapScan
import networkx as nx
from itertools import combinations
from web3 import Web3
import re
import shutil
import os
import json

from utils.data import (
    SUPPORTED_NETWORK,
    check_if_source_exists,
    check_if_supported_network_in_url,
    get_target_from_url,
    load_source,
)

app = Flask(__name__)
app_dir = os.path.dirname(os.path.realpath(__file__))
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def generate_session_data(path, api_key=None):
    if not path:
        return "Missing target network:0x...", 400

    try:
        network, address = path.split(":")
    except ValueError:
        return "Invalid path format. Expected network:0x...", 400

    if network + ":" not in SUPPORTED_NETWORK.keys():
        return f"Unsupported network: {network}", 400

    if not Web3.is_address(address):
        return f"Invalid Ethereum address: {address}", 400

    session_data_path = check_if_source_exists(path)

    if session_data_path:
        data = load_source(session_data_path)
        return data

    try:
        if api_key:
            source = DownloaderClass(path, api_key)
            source.run_crytic()
        else:
            source = DownloaderClass(path)
            source.run_crytic()
    except Exception as e:
        print(f"Error while downloading source: {e}")
        print(f"Verify contract address, network or etherscan API_KEY ...")

        if os.path.exists(source.output_dir):
            try:
                shutil.rmtree(source.output_dir)
            except Exception as e:
                print(f"Error deleting directory: {e}")
        else:
            print(f"Directory does not exist: {source.output_dir}")

        return {"error": str(e)}, 400

    try:
        target = AnalyticsClass(
            source.crytic_root_file,  # target path/Contract.sol
            source.root_contract,  # target Contract name (of crytic_root_file)
            source.output_dir,  # where to find slither.config.json
        )
        target.run_analysis()
    except Exception as e:
        print(f"Error running AnalyticsClass: {e}")
        return {"error": str(e)}, 400

    try:
        prompter = PromptClass()
        all_strategies = prompter.get_all_prompt_strategies()
        for function_data in target.output_functions:
            function_data["description"] = get_function_description(
                source.root_contract, function_data
            )
            function_data["prompts"] = {strategy: "" for strategy in all_strategies}
    except Exception as e:
        print(f"Error generating available strategies: {str(e)}")

    data = {
        "network_info": source.contract_info,
        "contract_data": target.output_contract,
        "functions_data": target.output_functions,
        "variables_data": target.output_variables,
        "source_code": target.output_sources,
        "scan_results": target.output_scan,
    }

    try:
        contract_map = ContractMap(path, data)
        contract_map.run_map()

        # NOTE: Generates data for a single contract only!
        target.output_contract["external_calls"] = contract_map.external_calls
        target.output_contract["external_addresses"] = contract_map.external_addresses

        for var in target.output_variables:
            for key, value in contract_map.external_addresses.items():
                if var["variable_name"] == key:
                    var["address"] = value

    except Exception as e:
        print(f"Error fetching variable addresses: {e}")

    # NOTE: sessionData.json is created only here
    with open(os.path.join(source.output_dir, "sessionData.json"), "w") as f:
        json.dump(data, f, indent=4)

    return data, 200


def compile_from_network(path, crawl=None):
    data, status_code = generate_session_data(path)

    if status_code != 200:
        return data, status_code

    # NOTE: Only used on first compilation
    if crawl:
        try:
            contract_map_scan = ContractMapScan(crawl)
            contract_map_scan.get_external_sources()
        except Exception as e:
            print(f"Error running ContractMapScan: {e}")

    return data, status_code


# region Endpoints
###################################################################################
###################################################################################
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:

            path = request.form["path"]
            crawl = request.form["crawl"]

            if crawl == "":
                crawl = None

            path_type = sort_path(path)

            # target input etherscan url
            if path_type == "network_url_target":
                network_address = get_target_from_url(path)
                if network_address:
                    data, status_code = compile_from_network(network_address, crawl)
                    if status_code == 400:
                        return data, status_code
                    else:
                        return jsonify(data)
                else:
                    return "Invalid URL target", 400

            # target input <network>:<address>
            if path_type == "network_target":
                existing_data = _get_session_data(path)
                if existing_data:
                    return jsonify(existing_data)
                data, status_code = compile_from_network(path, crawl)
                if status_code != 200:
                    return data, status_code
                else:
                    return jsonify(data)

            # target input ~/files/out/path/to/dir
            if path_type == "dir_target":
                session_data_path = os.path.join(path, "sessionData.json")
                if os.path.isfile(session_data_path):
                    return jsonify(load_source(session_data_path))
                else:
                    return "Invalid directory target", 400

            # target input git clone
            if path_type == "repo_target" or path_type == "file_target":
                message = (
                    f"Compiling from GitHub repository is not supported yet: {path}"
                )
                return jsonify({"message": message}), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        return render_template("index.html")


@app.route("/generate_session_data", methods=["POST"])
def generate_session_data_endpoint():
    path = request.json.get("path")
    data, status_code = generate_session_data(path)

    if status_code != 200:
        return (
            jsonify({"message": "Generating session data for external target failed"}),
            400,
        )

    return jsonify(data)


@app.route("/protocol_analysis", methods=["GET"])
def protocol_analysis():
    crawl_level = int(0)
    contract_map_scan = ContractMapScan(crawl_level)
    contract_map_scan.gen_protocol_graph()
    protocol_data = nx.node_link_data(contract_map_scan.graph)

    strongly_connected_components = list(
        nx.strongly_connected_components(contract_map_scan.graph)
    )
    subgraphs = []

    # Create a subgraph for each strongly connected component
    for component in strongly_connected_components:
        subgraph = contract_map_scan.graph.subgraph(component)
        subgraph_data = nx.node_link_data(subgraph)
        # Check if the subgraph has links
        if subgraph_data["links"]:  # This checks if the 'links' list is not empty
            subgraphs.append(subgraph_data)  # Only add subgraphs with non-empty links


@app.route("/protocol_view", methods=["GET"])
def protocol_view():
    crawl_level = int(0)
    contract_map_scan = ContractMapScan(crawl_level)
    contract_map_scan.gen_protocol_graph()

    if ZERO_ADDRESS in contract_map_scan.graph:
        contract_map_scan.graph.remove_node(ZERO_ADDRESS)

    protocol_data = nx.node_link_data(contract_map_scan.graph)

    degree_centrality = nx.degree_centrality(contract_map_scan.graph)
    in_degree_centrality = nx.in_degree_centrality(contract_map_scan.graph)
    out_degree_centrality = nx.out_degree_centrality(contract_map_scan.graph)

    threshold = np.percentile(list(degree_centrality.values()), 75)

    core_periphery_map = {
        node: "core" if centrality > threshold else "periphery"
        for node, centrality in degree_centrality.items()
    }

    scc_ids = set()
    scc_sizes = []
    cluster_strength = 0
    for component in nx.strongly_connected_components(contract_map_scan.graph):
        subgraph = contract_map_scan.graph.subgraph(component)
        if subgraph.size() > 0:
            scc_ids.update(component)
            scc_sizes.append(len(component))
            cluster_strength += len(component) * nx.density(subgraph)

    num_nodes = len(contract_map_scan.graph.nodes())
    num_edges = len(contract_map_scan.graph.edges())

    network_size_metric = (
        (2 * num_nodes * num_edges) / (num_nodes + num_edges)
        if num_nodes > 0 and num_edges > 0
        else 0
    )

    isolates = list(nx.isolates(contract_map_scan.graph))
    core_nodes_count = sum(
        1
        for node in contract_map_scan.graph.nodes()
        if core_periphery_map[node] == "core"
    )
    periphery_nodes_count = sum(
        1
        for node in contract_map_scan.graph.nodes()
        if core_periphery_map[node] == "periphery"
    )

    core_node_centralities = {
        node: centrality
        for node, centrality in degree_centrality.items()
        if core_periphery_map[node] == "core"
    }
    periphery_node_centralities = {
        node: centrality
        for node, centrality in degree_centrality.items()
        if core_periphery_map[node] == "periphery"
    }

    # Calculate average centralities
    average_core = (
        np.mean(list(core_node_centralities.values())) if core_node_centralities else 0
    )
    average_periphery = (
        np.mean(list(periphery_node_centralities.values()))
        if periphery_node_centralities
        else 0
    )

    # Min and Max Centrality Core and Periphery Nodes
    max_core_node = max(
        core_node_centralities, key=core_node_centralities.get, default=None
    )
    min_core_node = min(
        core_node_centralities, key=core_node_centralities.get, default=None
    )
    max_periphery_node = max(
        periphery_node_centralities, key=periphery_node_centralities.get, default=None
    )
    min_periphery_node = min(
        {
            node: centrality
            for node, centrality in periphery_node_centralities.items()
            if centrality > 0
        },
        key=periphery_node_centralities.get,
        default=None,
    )

    # Add additional data to nodes in protocol_data
    for node in protocol_data["nodes"]:
        node_id = node["id"]
        node.update(
            {
                "core_periphery": core_periphery_map.get(node_id, "not classified"),
                "scc_active": node_id in scc_ids,
                "degree_centrality": degree_centrality.get(node_id, 0),
                "in_degree_centrality": in_degree_centrality.get(node_id, 0),
                "out_degree_centrality": out_degree_centrality.get(node_id, 0),
            }
        )

    # Collect summary statistics in a separate dictionary to include in protocol_data
    protocol_data["statistics"] = {
        "network_size_metric": network_size_metric,
        "threshold": threshold,
        "average_degree": np.mean(list(degree_centrality.values())),
        "average_in_degree": np.mean(list(in_degree_centrality.values())),
        "average_out_degree": np.mean(list(out_degree_centrality.values())),
        "max_degree": max(list(degree_centrality.values())),
        "min_degree": min(value for value in degree_centrality.values() if value > 0),
        "sum_of_all_nodes": num_nodes,
        "sum_of_all_edges": num_edges,
        "sum_of_isolates": len(isolates),
        "sum_of_core_nodes": core_nodes_count,
        "sum_of_periphery_nodes": periphery_nodes_count,
        "cluster_count": len(scc_sizes),
        "cluster_strength": cluster_strength,
        "cluster_sizes": sorted(scc_sizes, reverse=True),
        "average_core_centrality": average_core,
        "average_periphery_centrality": average_periphery,
        "max_core_node": max_core_node,
        "max_core_node_label": (
            contract_map_scan.graph.nodes[max_core_node]["label"]
            if max_core_node
            else None
        ),
        "max_core_node_centrality": (
            core_node_centralities.get(max_core_node) if max_core_node else None
        ),
        "min_core_node": min_core_node,
        "min_core_node_label": (
            contract_map_scan.graph.nodes[min_core_node]["label"]
            if min_core_node
            else None
        ),
        "min_core_node_centrality": (
            core_node_centralities.get(min_core_node) if min_core_node else None
        ),
        "max_periphery_node": max_periphery_node,
        "max_periphery_node_label": (
            contract_map_scan.graph.nodes[max_periphery_node]["label"]
            if max_periphery_node
            else None
        ),
        "max_periphery_node_centrality": (
            periphery_node_centralities.get(max_periphery_node)
            if max_periphery_node
            else None
        ),
        "min_periphery_node": min_periphery_node,
        "min_periphery_node_label": (
            contract_map_scan.graph.nodes[min_periphery_node]["label"]
            if min_periphery_node
            else None
        ),
        "min_periphery_node_centrality": (
            periphery_node_centralities.get(min_periphery_node)
            if min_periphery_node
            else None
        ),
    }

    nodes = protocol_data["nodes"]
    stats = protocol_data["statistics"]

    print("protocol_data[statistics]:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("protocol_data[nodes]:")
    for node in nodes:
        print("Node:", node["id"])
        for key, value in node.items():
            print(f"  {key}: {value}")

    return jsonify(protocol_data)


@app.route("/protocol_view.html")
def protocol_view_html():
    return render_template("protocol_view.html")


@app.route("/get_session_data", methods=["GET"])
def get_session_data():
    path = request.args.get("path")
    data = _get_session_data(path)
    if data:
        return jsonify(data)
    else:
        return "Session data not found", 404


@app.route("/report", methods=["GET"])
def report():
    return render_template("report.html")


@app.route("/list_sessions", methods=["GET"])
def list_sessions():
    try:
        base_path = os.path.join(app_dir, "files", "out")
        if not os.path.exists(base_path):
            return jsonify({"error": f"Directory {base_path} does not exist"}), 500

        directories = next(os.walk(base_path))[1]
        result = {
            directory: os.path.join(base_path, directory) for directory in directories
        }
        return jsonify(result)
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return jsonify({"error": "Failed to list sessions", "details": str(e)}), 500


@app.route("/prompt", methods=["POST"])
def prompt():
    try:
        data = request.get_json()
        function_data = data.get("function_data")
        strategy_for_function = data.get("strategy_for_function")

        prompter = PromptClass()
        prompter.load_prompt_strategy(strategy_for_function)
        prompt = prompter.construct_function_prompt(function_data)

        return jsonify({strategy_for_function: prompt})
    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Error generating prompt for strategy {strategy_for_function}: {str(e)}"
                }
            ),
            400,
        )


@app.route("/filter", methods=["POST"])
def filter():
    data = request.json
    sessionData = data.get("sessionData")
    search_criteria = data.get("searchCriteria")

    filtered_functions = filter_functions(sessionData, search_criteria)

    return jsonify(filtered_functions)


@app.route("/filter_scan", methods=["POST"])
def filter_scan():
    data = request.json
    sessionData = data.get("sessionData")
    search_criteria = data.get("searchCriteria")

    filtered_scan = filter_results(sessionData["scan_results"], search_criteria)

    return jsonify(filtered_scan)


# endregion

# region Helper Functions
###################################################################################
###################################################################################


def filter_results(scan_data, search_criteria):

    filtered_results = []

    for entry in scan_data:
        matches_criteria = True

        if (
            search_criteria.get("impact")
            and entry.get("impact") != search_criteria["impact"]
        ):
            matches_criteria = False

        if (
            search_criteria.get("check_scanned")
            and entry.get("check") != search_criteria["check_scanned"]
        ):
            matches_criteria = False

        if (
            search_criteria.get("function_scanned")
            and entry.get("full_name") != search_criteria["function_scanned"]
        ):
            matches_criteria = False

        if (
            search_criteria.get("contract_scanned")
            and entry.get("contract") != search_criteria["contract_scanned"]
        ):
            matches_criteria = False

        if matches_criteria:
            filtered_results.append(entry)

    return filtered_results


def filter_functions(search_data, search_criteria):
    functions_data = search_data.get("functions_data")
    scan_data = search_data.get("scan_results")
    function_name = search_criteria.get("functionName")
    filtered_functions = []

    # Preprocess scan_data based on impact criterion
    impact = search_criteria.get("impact")
    find_target_reachable = search_criteria.get("find_target_reachable")
    all_reachable_from = search_criteria.get("all_reachable_from")

    if find_target_reachable:
        find_target_matches = preprocess_find_target_reachable(
            functions_data, find_target_reachable
        )
    else:
        find_target_matches = None

    if all_reachable_from:
        all_reachable_from_matches = preprocess_all_reachable_from(
            functions_data, all_reachable_from
        )
    else:
        all_reachable_from_matches = None

    if impact:
        impact_matches = preprocess_scan_data_for_impact(scan_data, impact)
    else:
        impact_matches = None

    for function in functions_data:
        matches_criteria = True

        if function_name and function_name not in function.get(
            "function_canonical_name"
        ):
            matches_criteria = False

        if (
            search_criteria.get("visibility")
            and function.get("visibility") != search_criteria["visibility"]
        ):
            matches_criteria = False

        if search_criteria.get("priority") and function.get("priority") != int(
            search_criteria["priority"]
        ):
            matches_criteria = False

        if "hasModifiers" in search_criteria:
            has_modifiers = bool(function.get("modifiers"))
            if (search_criteria["hasModifiers"] == "true") != has_modifiers:
                matches_criteria = False

        if "hasInternalCalls" in search_criteria:
            has_internal_calls = bool(function.get("internal_calls"))
            if (search_criteria["hasInternalCalls"] == "true") != has_internal_calls:
                matches_criteria = False

        if "hasExternalCalls" in search_criteria:
            has_external_calls = bool(function.get("external_calls"))
            if (search_criteria["hasExternalCalls"] == "true") != has_external_calls:
                matches_criteria = False

        if "isInheritedFunction" in search_criteria:
            is_inherited = search_criteria["isInheritedFunction"] == "true"
            if bool(function.get("contract_inherited")) != is_inherited:
                matches_criteria = False

        if "containsAsm" in search_criteria:
            contains_asm = search_criteria["containsAsm"] == "true"
            if bool(function.get("contains_asm")) != contains_asm:
                matches_criteria = False

        if "lowLvlCall" in search_criteria:
            low_lvl_call = search_criteria["lowLvlCall"] == "true"
            if bool(function.get("low_level_calls")) != low_lvl_call:
                matches_criteria = False

        if "in_contract" in search_criteria:
            in_contract = search_criteria["in_contract"]
            if not function.get("contract_name") in in_contract:
                matches_criteria = False

        if "writing_to" in search_criteria:
            writing_to = search_criteria["writing_to"]
            if not any(
                var in writing_to for var in function.get("state_vars_written", [])
            ):
                matches_criteria = False

        if "reading_from" in search_criteria:
            reading_from = search_criteria["reading_from"]
            if not any(
                var in reading_from for var in function.get("state_vars_read", [])
            ):
                matches_criteria = False

        if "calling_external_contract" in search_criteria:
            calling_external_contract = search_criteria["calling_external_contract"]
            if not any(
                contract in calling_external_contract
                for contract in function.get("external_calls", [])
            ):
                matches_criteria = False

        # NOTE: function_body workaround, requires a PR to slihter to search in structs
        if "using_structure" in search_criteria:
            using_structure = search_criteria["using_structure"]
            if not any(
                structure in function.get("function_body", "")
                for structure in using_structure
            ):
                matches_criteria = False

        # NOTE: function_body workaround, requires a PR to slihter to search in events
        if "emitting" in search_criteria:
            emitting = search_criteria["emitting"]
            if not any(
                event in function.get("function_body", "") for event in emitting
            ):
                matches_criteria = False

        if all_reachable_from_matches is not None:
            # Check if there's a match for the current function in the all_reachable_from_matches list
            if not any(
                function.get("function_full_name") in reachable.values()
                for reachable in all_reachable_from_matches
            ):
                matches_criteria = False

        if find_target_matches is not None:
            # Check if there's a match for the current function in the find_target_matches list
            if not any(
                function.get("function_full_name") in target_match.values()
                for target_match in find_target_matches
            ):
                matches_criteria = False

        # Adjusted impact criterion check
        if impact_matches is not None:
            # Check if there's a match for the current function in the impact_matches dictionary
            if not impact_matches.get(function.get("function_full_name")):
                matches_criteria = False

        if matches_criteria:
            # If all criteria match, append the function
            filtered_functions.append(function)

    return filtered_functions


def filter_variables(search_data, search_criteria):
    pass


def preprocess_all_reachable_from(functions_data, targets):
    # Initialize a set to keep track of all functions that are reachable from any of the targets
    all_reachable_from_any_target = set()

    # Iterate over each target to accumulate reachable functions
    for target in targets:
        for function in functions_data:
            if function.get("function_full_name") == target:
                # Update the set with reachable functions for this target
                all_internal = set(function.get("internal_calls", []))
                all_external = set(function.get("external_calls_functions", []))
                all_calls = all_internal.union(all_external)
                all_reachable_from_any_target.update(all_calls)

    # Filter the functions_data to include only functions that are reachable from at least one of the targets
    filtered_functions = [
        function
        for function in functions_data
        if function.get("function_full_name") in all_reachable_from_any_target
    ]

    return filtered_functions


def preprocess_find_target_reachable(functions_data, targets):
    # Initialize a set to keep track of all functions that are reachable from any of the targets
    all_reaching_target = set()

    # Iterate over each target to accumulate reachable functions
    for target in targets:
        for function in functions_data:
            all_internal = set(function.get("internal_calls", []))
            all_external = set(function.get("external_calls_functions", []))
            all_calls = all_internal.union(all_external)
            if target in all_calls:
                all_reaching_target.add(function.get("function_full_name"))

    # Filter the functions_data to include only functions that are reachable from at least one of the targets
    filtered_functions = [
        function
        for function in functions_data
        if function.get("function_full_name") in all_reaching_target
    ]

    return filtered_functions


def preprocess_scan_data_for_impact(scan_data, impact):
    # Maps function full names to whether they have a matching impact entry in scan_data
    impact_matches = {}
    for entry in scan_data:
        if entry.get("impact") == impact:
            impact_matches[entry.get("full_name")] = True
    return impact_matches


def _get_session_data(path):
    """
    Returns the session data from files/out/$network:address if it exists, otherwise returns None.
    """
    session_data_path = check_if_source_exists(path)
    if session_data_path:
        data = load_source(session_data_path)
        return data
    return None


def sort_path(path):
    # Check if target is a GitHub repository
    if re.match(r"^https://github\.com/[^/]+/[^/]+/?$", path):
        return "repo_target"
    # Check if target is a GitHub file
    elif re.match(r"^https://github\.com/[^/]+/[^/]+/blob/.*$", path):
        return "file_target"
    # Check if target is of the form network:address
    elif ":" in path and not "/" in path:
        return "network_target"
    # Check if target is a directory /path/to/directory
    elif os.path.isdir(path):
        return "dir_target"
    # Check if target is a URL containing a supported network
    elif check_if_supported_network_in_url(path):
        return "network_url_target"


def get_function_description(main_contract, function_data):
    visibility = f"<strong>{function_data.get('visibility', 'N/A')}</strong>"
    contract_name = f"<strong>{function_data.get('contract_name', 'Unknown')}</strong>"
    isInherited = (
        f"inherited in <strong>{main_contract}</strong>"
        if function_data.get("contract_inherited", False)
        else ""
    )
    hasModifiers = (
        "has modifier(s)"
        if function_data.get("modifiers") and len(function_data["modifiers"]) > 0
        else "has no modifiers"
    )
    modifiers_list = ", ".join(function_data.get("modifiers", [])) or ""
    if modifiers_list:
        modifiers_list = f"<strong>{modifiers_list}</strong>"
    basic_codes = function_data.get("basic_codes", "")
    if basic_codes:
        basic_codes = f"<strong>{basic_codes}</strong>"
    else:
        basic_codes = "<strong>no known 3rd party code</strong>"
    external_calls_count = len(function_data.get("external_calls", []))
    external_calls_contract_list = list(
        set(
            [
                f"<strong>{call.split('.')[0]}</strong>"
                for call in function_data.get("external_calls", [])
            ]
        )
    )
    internal_calls_count = len(function_data.get("internal_calls", []))
    internal_calls_list = (
        ", ".join(
            [
                f"<strong>{call}</strong>"
                for call in function_data.get("internal_calls", [])
            ]
        )
        or ""
    )
    description = (
        f"Is {visibility}. Declared in {contract_name} {isInherited} and {hasModifiers} {modifiers_list}. "
        f"Implements {basic_codes}. "
        f"{external_calls_count} external calls {external_calls_contract_list} and {internal_calls_count} internal calls {internal_calls_list}. "
    )

    return description


# endregion

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
