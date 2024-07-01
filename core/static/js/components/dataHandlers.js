import {
  displayScanResultsSection,
  createFunctionDataView,
  createContractDataView,
  createSourceCodeView,
} from "./ui.js";

import { initializeLoadData } from "./navigation.js";
import {
  sortPath,
  getSessionData,
  initScanDropdowns,
  getTargetFromUrl,
} from "./utils.js";

export var selectedActionTargets = [];

export function loadData() {
  var button = document.querySelector("#inputGroup button");
  button.textContent = "Loading...";

  var path = document.getElementById("pathInput").value;
  var crawl = document.getElementById("crawlInput").value;

  // Check and transform the path if it's a supported network URL
  var sortedPath = sortPath(path);

  if (sortedPath === "network_url_target") {
    var targetPath = getTargetFromUrl(path);
    if (targetPath) {
      path = targetPath;
    }
  }

  if (localStorage.getItem(path)) {
    window.history.pushState(path, "", `/?session_id=${path}`);
    initializeLoadData(path);
  } else {
    fetch("/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body:
        "path=" +
        encodeURIComponent(path) +
        "&crawl=" +
        encodeURIComponent(crawl),
    })
      .then((response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(text);
          });
        }
        return response.json();
      })
      .then((data) => {
        localStorage.setItem(path, JSON.stringify(data));
        window.history.pushState(path, "", `/?session_id=${path}`);

        displayScanResultsSection(data.scan_results);
        initScanDropdowns();
        document.getElementById("functionDisplay").innerHTML =
          createFunctionDataView(data.functions_data);
        document.getElementById("contractDisplay").innerHTML =
          createContractDataView(
            data.network_info,
            data.contract_data,
            data.variables_data
          );
        document.getElementById("searchDisplay").style.display = "block";
        document.getElementById("criteriaDisplay").style.display = "block";
        createSourceCodeView(data.source_code);
        button.textContent = "Load";
      })
      .catch((error) => {
        console.error("Error:", error);
        document.getElementById("functionDisplay").innerHTML =
          "<strong>Wrong Input:</strong> " + error.message;
      });
  }
}

export function filterData() {
  var form = document.getElementById("searchForm");
  var formData = new FormData(form);
  var searchCriteria = Object.fromEntries(formData.entries());
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);
  // Ugly hack because we wrap everything in <form>> in html
  delete searchCriteria["findAction[]"];
  delete searchCriteria["findTarget[]"];

  for (let key in searchCriteria) {
    if (searchCriteria[key] === "") {
      delete searchCriteria[key];
    }
  }

  // Transform selectedActionTargets into the desired flat structure
  selectedActionTargets.forEach((actionObj) => {
    if (searchCriteria[actionObj.action]) {
      // Merge if there's already an entry for this action
      searchCriteria[actionObj.action] = [
        ...new Set([...searchCriteria[actionObj.action], ...actionObj.targets]),
      ];
    } else {
      // Create a new entry if it doesn't exist
      searchCriteria[actionObj.action] = actionObj.targets;
    }
  });
  fetch("/filter", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ searchCriteria, sessionData }),
  })
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("functionDisplay").innerHTML =
        createFunctionDataView(data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

export function filterScanResults() {
  var form = document.getElementById("scanResultFilterForm");
  var formData = new FormData(form);
  var searchCriteria = Object.fromEntries(formData.entries());

  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);

  fetch("/filter_scan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ searchCriteria, sessionData }),
  })
    .then((response) => response.json())
    .then((data) => {
      displayScanResultsSection(data);
      document.getElementById("scanResultsContainer").style.display = "block";
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

export function handleTargetSelection(action, target) {
  let actionObj = selectedActionTargets.find((a) => a.action === action);
  if (!actionObj) {
    actionObj = { action: action, targets: [] };
    selectedActionTargets.push(actionObj);
  }

  // Check if the target is already included for the action
  const targetIndex = actionObj.targets.indexOf(target);

  // If found, remove the target (deselect it)
  if (targetIndex > -1) {
    actionObj.targets.splice(targetIndex, 1);
  } else {
    // Target not found, so add it (select it)
    actionObj.targets.push(target);
  }
}

export function resetSelections() {
  selectedActionTargets = [];
  document.getElementById("searchForm").reset();
  document.getElementById("criteriaDisplay").innerHTML = "";
  document.getElementById("findTarget").innerHTML =
    '<option value="">Select Target</option>';
}

export function updateCriteriaDisplay() {
  var form = document.getElementById("searchForm");
  var formData = new FormData(form);
  var searchCriteria = Object.fromEntries(formData.entries());

  delete searchCriteria["findAction[]"];
  delete searchCriteria["findTarget[]"];

  for (let key in searchCriteria) {
    if (searchCriteria[key] === "") {
      delete searchCriteria[key];
    }
  }

  var criteriaText = "<strong>Active Filter:</strong><br>";
  for (let key in searchCriteria) {
    criteriaText += `<strong>${key}</strong>: ${searchCriteria[key]}<br>`;
  }

  selectedActionTargets.forEach((actionObj) => {
    criteriaText += `<strong>${
      actionObj.action
    }</strong>: ${actionObj.targets.join(", ")}<br>`;
  });

  document.getElementById("criteriaDisplay").innerHTML = criteriaText;
  document.getElementById("criteriaDisplay").style.display = "block";
}

export function populateTargets(actions) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);

  var targetDropdown = document.getElementById("findTarget");
  targetDropdown.innerHTML = '<option value="">Select Target</option>'; // Reset dropdown

  var targets = [];

  actions.forEach((action) => {
    switch (action) {
      case "emitting":
        targets = sessionData.contract_data.events.map((event) => ({
          name: event,
          value: event,
        }));
        break;
      case "writing_to":
      case "reading_from":
        targets = sessionData.contract_data.all_variables.map((variable) => ({
          name: variable,
          value: variable,
        }));
        break;
      case "calling_external_contract":
        targets = sessionData.contract_data.all_external_calls.map((call) => ({
          name: call,
          value: call,
        }));
        break;
      case "find_target_reachable":
      case "all_reachable_from":
        targets = sessionData.contract_data.all_function_names.map((func) => ({
          name: func,
          value: func,
        }));
        break;
      case "using_structure":
        targets = sessionData.contract_data.structures.map((struct) => ({
          name: struct,
          value: struct,
        }));
        break;
      case "in_contract":
        targets = [
          sessionData.contract_data.contract_name,
          ...sessionData.contract_data.immediate_inheritance,
        ].map((contract) => ({ name: contract, value: contract }));
        break;
    }
  });

  targets = Array.from(
    new Set(targets.map((target) => JSON.stringify(target)))
  ).map((str) => JSON.parse(str));

  // Populate the target dropdown with options based on the selected action
  targets.forEach(function (target) {
    var option = new Option(target.name, target.value);
    targetDropdown.add(option);
  });
}
