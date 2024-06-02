import {
  populateSessionStorageDropdown,
  initializePageWithData,
  initializeLoadData,
  getActiveSession,
  clearData,
} from "./navigation.js";

import {
  loadData,
  updateCriteriaDisplay,
  populateTargets,
  handleTargetSelection,
} from "./dataHandlers.js";

document.addEventListener("DOMContentLoaded", function () {
  hljs.highlightAll();
  // initializePageWithData();
  populateSessionStorageDropdown();

  const urlParams = new URLSearchParams(window.location.search);
  const sessionID = urlParams.get("session_id");

  if (sessionID) {
    initializeLoadData(sessionID);
  }

  document.getElementById("loadDataButton").addEventListener("click", loadData);
  document
    .getElementById("reportButton")
    .addEventListener("click", getActiveSession);
  document
    .getElementById("clearDataButton")
    .addEventListener("click", clearData);
  document
    .getElementById("openTargetsButton")
    .addEventListener("click", () =>
      window.open("http://127.0.0.1:8001", "_blank")
    );
  document
    .getElementById("protocolViewButton")
    .addEventListener(
      "click",
      () => (window.location.href = "protocol_view.html")
    );
});

document
  .getElementById("searchForm")
  .addEventListener("change", updateCriteriaDisplay());

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
