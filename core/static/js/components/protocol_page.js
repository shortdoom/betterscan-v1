import { populateSessionStorageDropdown } from "./navigation.js";
import {createProtocolMap} from "./protocol_viz.js";

document.addEventListener("DOMContentLoaded", function () {
  populateSessionStorageDropdown();
  createProtocolMap();
});
