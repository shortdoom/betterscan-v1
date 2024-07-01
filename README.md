# Betterscan v0.1

Betterscan is a security tool designed to parse, analyze, and display data from any EVM-based smart contracts. It provides a visual representation of the contract's source code and its dependencies. The tool allows you to search for specific functions, variables, and contracts while also finding intersections within all data. You can run automatic detectors on the target contract and filter the results based on impact and check type.

Betterscan works with both individual contract addresses and lists of addresses. When list of addresses is provided, you'll be presented with a "protocol view" of all interconnected contracts.

It's integrated with [immunefi-terminal](https://github.com/shortdoom/immunefi-terminal) to quickly download, parse, and browse potential bounty targets, or to just have a large dataset of contract source code to analyze.

Read more here about one of the use cases for Betterscan:

# Install & Run

`chmod +x setup.sh`

`./setup.sh`

then

`python run.py` (from your newly created `venv`)

If you want to set it up manually, just inspect the `setup.sh` and follow the instructions accordingly.

Betterscan Dashboard is running on: `127.0.0.1:5000`

Datasette Dashboard is running on `127.0.0.1:8001`

# Features

Out-of-the-box compilation of Etherscan explorers verified source code (multiple networks)

Protocol view of interconnected contracts 

Inspect details of contracts, functions, variables, internal and external calls, modifiers, expressions, low-level calls, inline assembly, and more

Advanced filtering features allow direct querying of function flows, finding reads/writes, zeroing in on low-level calls, and more. All filters can be freely mixed

Automatic slither, slitherin, and semgrep detectors run on the target contract

Set up custom prompts for your LLM-based audits

# Demo

![App navigation](/docs/images/navigation1.png)
![Protocol view](/docs/images/protocol_view.png)
![Contract data](/docs/images/contract_data1.png)
![Search functions](/docs/images/search_functions1.png)
![Search detectors](/docs/images/search_detectors1.png)
![Functions view](/docs/images/functions_view1.png)

# Dashboard sections

### Navigation

Three types of inputs are allowed:

Network:address input like: `mainnet:0x0000000000000000000000000000000000000000`

URL input like: `https://etherscan.io/address/0x0000000000000000000000000000000000000000`

Localhost directory path: `core/files/out/mainnet:0x0000000000000000000000000000000000000000` (experimental, compilations tend to fail)

After successfully downloading the source and generating sessionData (AST), artifact targets become available to jump to from the dropdown. You can also clear unused data. LocalStorage has a 5MB limit.

### Contract Data

Four types of data are displayed in this section:

Protocol/Network view, Network Information, Contract Data, and State Variables.

In V1, only State Variables allow jumping to definitions. Other types of information are just textual.

### Protocol view

When Betterscan is used with list of addresses as an argument while using the `runner.py` script (or, if enough of the contracts is provided manually through the interface) a protocol-view will be available on both main page and individual session page. Protocol view shows external calls connections between multiple separate contracts. 

### Search Functions

The main functionality of Betterscan is a search functionality. You can freely mix different filters, and the function display will return matching function definitions. You can "Reset" the search at any time or add indefinitely to the existing query. When searching is active, you'll notice the "Active Filters" section appearing, informing you about the currently displayed query.

### Search Detectors

Similarly to the Search Functions above, you can search for detector results from slither, slitherin, and semgrep. This section is not connected with the Search Functions section.

### Function & Source Code Views

The Functions and Source Code display is where the results of your filtering are displayed. Each function definition contains a lot of additional information you can inspect. You are free to open an unlimited number of views at the same time.

# Misc

**Working directly with python files**

`python run.py` will start the application. To send POST request to the application the Flask server needs to be running.

`python runner.py` allows to POST *targets* extracted from datasette or csv file to the `app.py` from Python without the UI. It's a useful feature for building protocol view. Go to the deployments page of your favorite protocol, copy addresses line-by-line into the .csv file and run `python runner.py --csv TARGETS.csv --crawl_level 0`. crawl_level argument will deep crawl every single contract on the list to discover contracts. Run with `crawl_level 1` if you are just interested in most immediate external contract dependencies.