import os
import re
import json
from urllib.parse import urlparse

utils_dir = os.path.dirname(os.path.realpath(__file__))
core_dir = os.path.dirname(utils_dir)
files_dir = os.path.join(core_dir, "files", "out")

#################### APP.PY ####################

SUPPORTED_NETWORK = {
    "mainet:": "etherscan.io",
    "optim:": "optimistic.etherscan.io",
    "goerli:": "goerli.etherscan.io",
    "sepolia:": "sepolia.etherscan.io",
    "tobalaba:": "tobalaba.etherscan.io",
    "bsc:": "bscscan.com",
    "testnet.bsc:": "testnet.bscscan.com",
    "arbi:": "arbiscan.io",
    "testnet.arbi:": "testnet.arbiscan.io",
    "poly:": "polygonscan.com",
    "mumbai:": "testnet.polygonscan.com",
    "avax:": "snowtrace.io",
    "testnet.avax:": "testnet.snowtrace.io",
    "ftm:": "ftmscan.com",
    "goerli.base:": "goerli.basescan.org",
    "base:": "basescan.org",
    "gno:": "gnosisscan.io",
    "polyzk:": "zkevm.polygonscan.com",
}

SUPPORTED_NETWORK = dict(
    sorted(SUPPORTED_NETWORK.items(), key=lambda item: -len(item[1]))
)


def check_if_source_exists(path):
    """
    Checks if a directory exists in the "files/out" directory that partially matches the provided path.
    If a matching directory is found and contains a sessionData.json file, returns the path to the sessionData.json file.
    Otherwise, returns None.
    """
    for root, dirs, _ in os.walk(files_dir):
        for dir_name in dirs:
            if path in dir_name:
                session_data_path = os.path.join(root, dir_name, "sessionData.json")
                if os.path.isfile(session_data_path):
                    return session_data_path
                else:
                    print(
                        f"check_if_source_exists: sessionData.json not found in: {dir_name}"
                    )

    return None


def check_if_supported_network_in_url(path):
    """
    Checks if the path contains any of the supported network URLs.
    Returns True if it does, otherwise returns False.
    """
    for network_url in SUPPORTED_NETWORK.values():
        if network_url in path:
            return True
    return False


def get_target_from_url(path):
    """
    Parses the given path to extract the Ethereum address and identifies the network.
    Returns a string in the format 'network:address' if successful.
    """
    parsed_url = urlparse(path)
    domain = parsed_url.netloc
    path_segments = parsed_url.path.split("/")
    eth_address = next(
        (
            segment
            for segment in path_segments
            if re.match(r"^0x[a-fA-F0-9]{40}$", segment)
        ),
        None,
    )

    if eth_address is None:
        return None

    for network, url in SUPPORTED_NETWORK.items():
        if url in domain:
            return f"{network}{eth_address}"

    return None


def load_source(file_path):
    """
    Loads the JSON data from a file.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def find_all_session_data_paths():
    dirs = os.listdir(files_dir)
    session_data_paths = []
    for dir_name in dirs:

        if os.path.isfile(os.path.join(files_dir, dir_name)):
            continue

        session_data_path = os.path.join(files_dir, dir_name, "sessionData.json")
        if os.path.isfile(session_data_path):
            session_data_paths.append(session_data_path)
        else:
            print(
                f"find_all_session_data_paths: sessionData.json not found in: {dir_name}"
            )

    return session_data_paths


def get_session_data(session_data_path):
    """
    Returns the session data from files/out/$network:address if it exists, otherwise returns None.
    """
    if session_data_path:
        data = load_source(session_data_path)
        return data
    return None
