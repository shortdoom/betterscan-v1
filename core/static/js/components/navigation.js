import {
  displayScanResultsSection,
  createFunctionDataView,
  createContractDataView,
  createSourceCodeView,
} from "./ui.js";

import { initScanDropdowns } from "./utils.js";

export async function fetchSessionData(sessionPath) {
  return fetch(`/get_session_data?path=${encodeURIComponent(sessionPath)}`)
    .then((response) => {
      if (!response.ok) {
        console.warn(`Could not fetch session data: ${response.statusText}`);
        return null;
      }
      return response.json();
    })
    .then((sessionData) => {
      if (sessionData) {
        localStorage.setItem(sessionPath, JSON.stringify(sessionData));
        return 200;
      } else {
        return null;
      }
    })
    .catch((error) => {
      console.error(`Error fetching session data: ${error}`);
      return null;
    });
}

export function clearData() {
  localStorage.clear();
  alert("All data cleared successfully. F5 to see changes.");
  populateSessionStorageDropdown();
}

export function jumpToSession(session_path) {
  window.history.pushState(session_path, "", `/?session_id=${session_path}`);
  initializeLoadData(session_path);
}

export function getActiveSession() {
  let url = new URL(window.location.href);
  let sessionId = url.searchParams.get("session_id");
  window.location.href = "/report?session_id=" + sessionId;
}

export function populateSessionStorageDropdown() {
  var select = document.createElement("select");
  select.id = "keysDropdown";

  select.onchange = function () {
    // jumpToSession(select.value);
    window.location.href = `/?session_id=${select.value}`;
  };

  var defaultOption = document.createElement("option");
  defaultOption.text = "Select a session";
  select.appendChild(defaultOption);

  fetch("/list_sessions")
    .then((response) => {
      if (!response.ok) {
        return response.text().then((text) => {
          throw new Error(text);
        });
      }
      return response.json();
    })
    .then((directories) => {
      Object.entries(directories).forEach(([directory]) => {
        var option = document.createElement("option");
        var parts = directory.split(":");
        option.value = parts.slice(0, 2).join(":");
        option.text = directory;
        select.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error fetching files/out directories:", error);
    });

  var container = document.getElementById("dropdownContainer");
  container.innerHTML = "";
  container.appendChild(select);
}

export function initializePageWithData() {
  const urlParams = new URLSearchParams(window.location.search);
  const sessionID = urlParams.get("session_id");

  if (sessionID) {
    const sessionData = JSON.parse(localStorage.getItem(sessionID));
    if (sessionData) {
      // hljs.highlightAll();
      displayScanResultsSection(sessionData.scan_results);
      initScanDropdowns();
      document.getElementById("functionDisplay").innerHTML =
        createFunctionDataView(sessionData.functions_data);
      document.getElementById("contractDisplay").innerHTML =
        createContractDataView(
          sessionData.network_info,
          sessionData.contract_data,
          sessionData.variables_data
        );
      document.getElementById("searchDisplay").style.display = "block";
      document.getElementById("criteriaDisplay").style.display = "block";
      createSourceCodeView(sessionData.source_code);
      document.getElementById("homepage").style.display = "none";
    } else {
      console.log("Session data not found for ID:", sessionID);
      initializeFileData(path);
    }
  }
}

export function initializeLoadData(path) {
  const localData = JSON.parse(localStorage.getItem(path));
  console.log("Local data found for ID:", path, localData)
  if (localData) {
    displayScanResultsSection(localData.scan_results);
    initScanDropdowns();
    document.getElementById("functionDisplay").innerHTML =
      createFunctionDataView(localData.functions_data);
    document.getElementById("contractDisplay").innerHTML =
      createContractDataView(
        localData.network_info,
        localData.contract_data,
        localData.variables_data
      );
    document.getElementById("searchDisplay").style.display = "block";
    document.getElementById("criteriaDisplay").style.display = "block";
    createSourceCodeView(localData.source_code);
    document.getElementById("homepage").style.display = "none";
  } else {
    console.log("Session data not found for ID:", path);
    initializeFileData(path);
  }
}

export async function initializeFileData(path) {
  const success = await fetchSessionData(path);
  if (success) {
    initializeLoadData(path);
  } else {
    console.log("Local file data not found for ID:", path);
  }
}
