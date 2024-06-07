import {
  populateSessionStorageDropdown,
  initializeLoadData,
  getActiveSession,
  clearData,
} from "./navigation.js";

import {
  loadData,
  updateCriteriaDisplay,
  populateTargets,
  handleTargetSelection,
  resetSelections,
  filterData,
  filterScanResults,
} from "./dataHandlers.js";

import {
  toggleScanResultsDisplay,
  gotoLinesInEditor,
  copyKeyContent,
} from "./ui.js";

import { createProtocolMap } from "./protocol_viz.js";

document.addEventListener("DOMContentLoaded", function () {
  hljs.highlightAll();
  populateSessionStorageDropdown();
  createProtocolMap("#protocol_viz");

  const urlParams = new URLSearchParams(window.location.search);
  const sessionID = urlParams.get("session_id");

  if (sessionID) {
    initializeLoadData(sessionID);
  }

  document.getElementById("loadDataButton").addEventListener("click", loadData);
});

const navButtons = document.getElementById("inputGroup");
navButtons
  .querySelector("#clearDataButton")
  .addEventListener("click", clearData);
navButtons
  .querySelector("#openTargetsButton")
  .addEventListener("click", () =>
    window.open("http://127.0.0.1:8001", "_blank")
  );

const resetButton = document.getElementById("resetSelectionsButton");
const searchButton = document.getElementById("filterDataButton");
const filterScanResultsButton = document.getElementById(
  "filterScanResultsButton"
);
const toggleScanResultsButton = document.getElementById(
  "toggleScanResultsButton"
);
const searchForm = document.getElementById("searchForm");

searchForm.addEventListener("change", updateCriteriaDisplay);

resetButton.addEventListener("click", function (event) {
  event.preventDefault();
  resetSelections();
});

searchButton.addEventListener("click", function (event) {
  event.preventDefault();
  filterData();
});

filterScanResultsButton.addEventListener("click", function (event) {
  event.preventDefault();
  filterScanResults();
});

toggleScanResultsButton.addEventListener("click", function (event) {
  event.preventDefault();
  toggleScanResultsDisplay();
});

document.body.addEventListener("click", function (event) {
  if (event.target.matches(".goto-lines-button")) {
    const contractName = event.target.getAttribute("data-contract-name");
    const startLine = parseInt(
      event.target.getAttribute("data-start-line"),
      10
    );
    const endLine = parseInt(event.target.getAttribute("data-end-line"), 10);
    gotoLinesInEditor(contractName, startLine, endLine);
  }
});

// Delegated event handler for "Copy" buttons
document.body.addEventListener("click", function (event) {
  if (event.target.matches(".copy-content-button")) {
    copyKeyContent();
  }
});

document.getElementById("findAction").addEventListener("change", function () {
  var actions = Array.from(this.selectedOptions).map((option) => option.value);
  populateTargets(actions);
});

document.getElementById("findTarget").addEventListener("change", function () {
  var selectedActions = Array.from(
    document.getElementById("findAction").selectedOptions
  ).map((option) => option.value);
  var selectedTargets = Array.from(this.selectedOptions).map(
    (option) => option.value
  );

  selectedActions.forEach((action) => {
    selectedTargets.forEach((target) => {
      handleTargetSelection(action, target);
    });
  });
});
