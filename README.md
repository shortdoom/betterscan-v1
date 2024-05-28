# Betterscan v0.1

Betterscan is a security tool designed to parse, analyze, and display data from any EVM-based smart contracts. It provides a visual representation of the contract's source code and its dependencies. The tool allows you to search for specific functions, variables, and contracts while also finding intersections within all data. You can run automatic detectors on the target contract and filter the results based on impact and check type.

It's integrated with [immunefi-terminal](https://github.com/shortdoom/immunefi-terminal) to quickly download, parse, and browse potential bounty targets, or to just have a large dataset of contract source code to analyze.

# Install & Run

`chmod +x setup.sh`

`./setup.sh`

then

`python run.py` (from your newly created `venv`)

If you want to set it up manually, just inspect the `setup.sh` and follow the instructions accordingly.

Betterscan Dashboard is running on: `127.0.0.1:5000`

Datasette Dashboard is running on `127.0.0.1:8001`

It's a Python app! VanillaJS + AceEditor are stored inside of the repository, you do not need to run npm! The ugly side effect is github suggesting that's a Javascript app.

# Features

Out-of-the-box compilation of Etherscan explorers verified source code (multiple networks)

Inspect details of contracts, functions, variables, internal and external calls, modifiers, expressions, low-level calls, inline assembly, and more

Advanced filtering features allow direct querying of function flows, finding reads/writes, zeroing in on low-level calls, and more. All filters can be freely mixed

Automatic slither, slitherin, and semgrep detectors run on the target contract

Set up custom prompts for your LLM-based audits

# Demo

![App navigation](/docs/images/navigation1.png)
![Contract data](/docs/images/contract_data1.png)
![Search functions](/docs/images/search_functions1.png)
![Search detectors](/docs/images/search_detectors1.png)
![Functions view](/docs/images/functions_view1.png)

# Dashboard sections

### Navigation

Three types of inputs are allowed:

Network:address input like: `mainnet:0x0000000000000000000000000000000000000000`

URL input like: `https://etherscan.io/address/0x0000000000000000000000000000000000000000`

Git repository like: `https://github.com/Project/repo` (requires Contract Name as an additional argument)

Localhost directory path: `core/files/out/mainnet:0x0000000000000000000000000000000000000000` (experimental, compilations tend to fail)

After successfully downloading the source and generating sessionData (AST), artifact targets become available to jump to from the dropdown. You can also clear unused data. LocalStorage has a 5MB limit.

### Contract Data

Three types of data are displayed in this section:

Network Information, Contract Data, and State Variables.

In V1, only State Variables allow jumping to definitions. Other types of information are just textual.

### Search Functions

The main functionality of Betterscan is a search functionality. You can freely mix different filters, and the function display will return matching function definitions. You can "Reset" the search at any time or add indefinitely to the existing query. When searching is active, you'll notice the "Active Filters" section appearing, informing you about the currently displayed query.

### Search Detectors

Similarly to the Search Functions above, you can search for detector results from slither, slitherin, and semgrep. This section is not connected with the Search Functions section.

### Function & Source Code Views

The Functions and Source Code display is where the results of your filtering are displayed. Each function definition contains a lot of additional information you can inspect. You are free to open an unlimited number of views at the same time.

# Misc

**Working directly with python files**

`cd core` and `python app.py` to run the version of the app used locally (relies on `files/out` directory as a filesystem db).

`cd datasette` and `python fetch_targets.py` to update the immunefi bounty database (and targets for mass scanning).

`utils/targets_run.py` is a middleware between Datasette and core Flask app. It allows to POST *targets* extracted from datasette to the `app.py` from Python, without the UI.


**Using with git clone directories**

`git clone` or just download contracts that will compile for slither inside `files/out`. run `python analyze.py /path/to/repo TargetContractName`, if it's *foundry* a `/path/to/repo` path should be the root of a template directory, adjust accordingly for other directory structures. `*_sessionData.json` file will be saved to the root of `file/out`, move this file to earlier cloned repository, remember to name it as `sessionData.json`, pass `path/to/repo` as an arg in `127.0.0.1` Flask app.