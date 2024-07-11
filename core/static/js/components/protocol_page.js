import { populateSessionStorageDropdown } from "./navigation.js";
import {createProtocolMap, createProtocolAnalysis} from "./protocol_viz.js";

document.addEventListener("DOMContentLoaded", async function () {
  populateSessionStorageDropdown();
  createProtocolMap();
  createProtocolAnalysis();
});

