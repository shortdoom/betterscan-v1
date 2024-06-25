import { populateSessionStorageDropdown } from "./navigation.js";
import {createProtocolMap, createProtocolAnalysis} from "./protocol_viz.js";

document.addEventListener("DOMContentLoaded", async function () {
  populateSessionStorageDropdown();
  await createProtocolMap();  // Ensure this completes before starting the next
  createProtocolAnalysis();
});

