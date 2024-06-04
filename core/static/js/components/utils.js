export const SUPPORTED_NETWORKS = {
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
};

export function getSessionData(session_path) {
    return JSON.parse(localStorage.getItem(session_path));
  }

export function isValidHttpUrl(string) {
  let url;

  try {
    url = new URL(string);
  } catch (_) {
    return false; // If an error is thrown, it is not a URL
  }

  return url.protocol === "http:" || url.protocol === "https:";
}

export function sortPath(path) {
  if (isValidHttpUrl(path) && checkIfSupportedNetworkInUrl(path)) {
    return "network_url_target";
  }
  if (path.startsWith("/")) {
    // Assuming directory paths start with '/'
    return "dir_target";
  }
  if (path.includes(":") && !path.includes("/")) {
    return "network_target"; // For <network>:<address> format
  }
  return null; // Default return if none of the above
}

export function checkIfSupportedNetworkInUrl(path) {
  if (!isValidHttpUrl(path)) {
    return false; // Immediately return false if it's not a valid URL
  }

  const domain = new URL(path).hostname;
  return Object.values(SUPPORTED_NETWORKS).some((networkUrl) =>
    domain.includes(networkUrl)
  );
}

export function getTargetFromUrl(path) {
  if (!isValidHttpUrl(path)) {
    return null; // Return null if not a valid URL
  }

  const url = new URL(path);
  const domain = url.hostname;
  const pathSegments = url.pathname.split("/");
  const ethAddress = pathSegments.find((segment) =>
    /^0x[a-fA-F0-9]{40}$/.test(segment)
  );

  if (!ethAddress) {
    return null;
  }

  const sortedNetworks = Object.entries(SUPPORTED_NETWORKS).sort(
    (a, b) => b[1].length - a[1].length
  );

  for (const [network, url] of sortedNetworks) {
    if (domain.includes(url)) {
      return `${network}${ethAddress}`; // Correct the network key by removing the colon
    }
  }
  return null;
}

export function isEmpty(value) {
  return (
    value === "" ||
    value === null ||
    (Array.isArray(value) && value.length === 0) ||
    (typeof value === "object" && Object.keys(value).length === 0)
  );
}

export function formatKeyData(key, keyData) {
  if (Array.isArray(keyData)) {
    keyData = keyData.join("<br>");
  } else if (typeof keyData !== "string") {
    keyData = JSON.stringify(keyData, null, 2);
  }
  return keyData;
}

export function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function unescapeHTML(str) {
  const temp = document.createElement("div");
  temp.innerHTML = str;
  return temp.textContent || temp.innerText || "";
}

export function toggleExpandableActive(currentElement) {
  // Allow expandable buttons to toggle without affecting others
  currentElement.classList.toggle("active");
}

export function orderSourceCodeFiles(
  contractName,
  contractsInherited,
  sourceCode
) {
  let orderedContracts = [contractName]; // Start with the main contract
  // Add inherited contracts in order
  if (contractsInherited && contractsInherited.length) {
    orderedContracts = orderedContracts.concat(contractsInherited);
  }
  // Add remaining contracts that are not in the inherited list
  Object.keys(sourceCode).forEach((key) => {
    if (!orderedContracts.includes(key)) {
      orderedContracts.push(key);
    }
  });
  return orderedContracts;
}

export function populateScanDropdown(dropdownId, dataKey) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);
  var dropdown = document.getElementById(dropdownId);
  dropdown.innerHTML = '<option value="">All</option>';

  const uniqueValues = Array.from(
    new Set(sessionData.scan_results.map((item) => item[dataKey]))
  ).sort(); // Sorting for better usability

  // Populate the dropdown with options
  uniqueValues.forEach((value) => {
    const option = new Option(value, value);
    dropdown.add(option);
  });
}

export function initScanDropdowns() {
  populateScanDropdown("checkSelect", "check");
  populateScanDropdown("functionSelect", "full_name");
  populateScanDropdown("contractSelect", "contract");
}
