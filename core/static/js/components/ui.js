import {
  unescapeHTML,
  isEmpty,
  getSessionData,
  orderSourceCodeFiles,
} from "./utils.js";
import "../editor/ace.js";

export var editor = null;

export function displayScanResultsSection(scanResults) {
  const scanResultsSection = document.getElementById("scanResultsSection");
  const scanResultsDisplay = document.getElementById("scanResultsDisplay");

  scanResultsSection.style.display = "block";

  if (!scanResults || scanResults.length === 0) {
    scanResultsDisplay.innerHTML = "<div>No detector data available</div>";
    return;
  }

  let content = `<div id="scanResultsContainer" style="display: none;">`;

  // Loop through each scan result to create its detailed view
  scanResults.forEach((item) => {
    content += `<div style="margin-bottom: 5px; padding-bottom: 5px;">`;
    Object.keys(item).forEach((propKey) => {
      if (propKey === "path") {
        content += `<div class="path" style="cursor: pointer; color: #0000a2;"><strong>jump-to-line:</strong> ${item[propKey]}</div>`;
      } else if (propKey === "full_name") {
        content += `<div class="function-name" style="cursor: pointer; color: #0000a2;"><strong>jump-to-function:</strong> ${item[propKey]}</div>`;
      } else if (propKey == "expressions") {
        content += `<div class="expressions" style="cursor: pointer; color: #0000a2;"><strong>jump-to-expression:</strong> ${item[propKey]}</div>`;
      } else {
        content += `<div><strong>${propKey}:</strong> ${item[propKey]}</div>`;
      }
    });
    content += `</div>`;
  });

  content += "</div>";
  scanResultsDisplay.innerHTML = content;
  scanResultsSection.style.display = "block";

  // Add click event listener to path elements
  document.querySelectorAll(".path").forEach((pathElement) => {
    pathElement.addEventListener("click", function () {
      const path = this.textContent.split(": ")[1];
      const pathParts = path.split("/");
      const contractName = pathParts[pathParts.length - 1]
        .split("#")[0]
        .split(".")[0];
      const [startLine, endLine] = pathParts[pathParts.length - 1]
        .split("#")[1]
        .split("-");
      gotoLinesInEditor(contractName, startLine, endLine);
    });
  });

  document.querySelectorAll(".expressions").forEach((expressions) => {
    expressions.addEventListener("click", function () {
      const expressions = this.textContent.split(": ")[1].split(",");
      jumpToExpression(expressions);
    });
  });

  document.querySelectorAll(".function-name").forEach((functionElement) => {
    functionElement.addEventListener("click", function () {
      const functionName = this.textContent.split(": ")[1];
      jumpToFunctionName(functionName);
    });
  });
}

export function jumpToFunctionName(functionName) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);

  const functionData = sessionData.functions_data.find(
    (func) => func.function_full_name === functionName
  );

  if (functionData) {
    start_line = functionData.line_numbers[0];
    end_line = functionData.line_numbers[1];
    gotoLinesInEditor(functionData.contract_name, start_line, end_line);
  }
}

export function jumpToExpression(expressions) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);

  const expressionData = sessionData.functions_data.find((func) =>
    expressions.some((expression) => func.expressions.includes(expression))
  );

  if (expressionData) {
    start_line = expressionData.line_numbers[0];
    end_line = expressionData.line_numbers[1];
    gotoLinesInEditor(expressionData.contract_name, start_line, end_line);
  }
}

export function toggleScanResultsDisplay() {
  const container = document.getElementById("scanResultsContainer");
  container.style.display =
    container.style.display === "none" ? "block" : "none";
}

export function createSourceCodeView(sourceCode) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);

  var sourceCodeDisplay = document.getElementById("sourceCodeDisplay");
  sourceCodeDisplay.innerHTML = "";

  var select = document.createElement("select");
  select.onchange = function () {
    var contractName = this.value;
    displaySourceCode(contractName, sourceCode[contractName].source_code);
  };
  sourceCodeDisplay.appendChild(select);

  var editorContainer = document.createElement("div");
  editorContainer.id = "editor";
  editorContainer.style.width = "100%";
  sourceCodeDisplay.appendChild(editorContainer);

  editor = ace.edit("editor");
  editor.setReadOnly(true);
  editor.setTheme("ace/theme/chrome");
  editor.session.setMode("ace/mode/solidity");

  editor.setOptions({
    maxLines: 150,
    minLines: 10,
  });

  // Adjust the editor's initial height to be more flexible
  editorContainer.style.minHeight = "100px";

  function displaySourceCode(contractName, source) {
    editor.setValue(source, -1); // -1 moves the cursor to the start
  }

  var orderedContracts = orderSourceCodeFiles(
    sessionData.contract_data.contract_name,
    sessionData.contract_data.immediate_inheritance,
    sourceCode
  );

  // Populate the dropdown with ordered source code files
  orderedContracts.forEach((contractName) => {
    var option = document.createElement("option");
    option.value = contractName;
    option.text = contractName;

    if (contractName === sessionData.contract_data.contract_name) {
      option.style.color = "red";
    } else if (
      sessionData.contract_data.immediate_inheritance &&
      sessionData.contract_data.immediate_inheritance.includes(contractName)
    ) {
      option.style.color = "orange";
    } else {
      option.style.color = "green";
    }
    select.appendChild(option);
  });

  // Optionally display first source code by default
  if (select.options.length > 0) {
    select.onchange();
  }
}

export function createContractDataView(
  networkInfo,
  contractData,
  variablesData
) {
  let content = "<div class='contract-section'>";
  if (!networkInfo && !contractData) {
    return content + "<div>No contract information available</div></div>";
  }

  content += createContractDetailDataView("Network Information", networkInfo);
  content += createContractDetailDataView("Contract Data", contractData);

  content += createContractDetailDataView("State Variables", variablesData);

  document.querySelector("body").addEventListener("click", function (event) {
    let element = event.target;
    while (element) {
      if (element.matches(".variable-name")) {
        const contractName = element.dataset.contractName;
        const startLine = element.dataset.startLine;
        const endLine = element.dataset.endLine;
        gotoLinesInEditor(contractName, startLine, endLine);
        break;
      }
      element = element.parentElement;
    }
  });

  return content + "</div>";
}

export function createFunctionDataView(data) {
  if (!data || !data.length) {
    return "<div>No data matching criteria found</div>";
  }

  let priorityGroups = { 1: "", 2: "", 3: "" };
  data.forEach((item) => {
    if (item && item.priority && priorityGroups[item.priority] !== undefined) {
      let dataInfoContent = formatFunctionData(item);
      priorityGroups[item.priority] += `
            <div class="data-section">
              <button class="collapsible selectable-text">${item.function_full_name}</button>
                
              <div class="function-content">
                    <div class="data-info">${dataInfoContent}</div>
                    <div class="key-content" style="display: none;"></div> <!-- Single key-content area -->
                </div>
            </div>
        `;
    }
  });

  let content = "";

  // Append the priority groups to the content
  Object.keys(priorityGroups).forEach((priority) => {
    if (priorityGroups[priority]) {
      let priorityLabel =
        priority == 1
          ? "Write (public/external)"
          : priority == 2
          ? "Write (internal/private)"
          : priority == 3
          ? "Read (view/pure)"
          : `Priority ${priority}`;
      content += `
            <div class="priority-group">
                <h2>${priorityLabel}</h2>
                ${priorityGroups[priority]}
            </div>
        `;
    }
  });
  return content;
}

export function createVariableDataView(dataObject) {
  let content = "";

  // Organize state variables by contract name
  let contracts = {};
  dataObject.forEach((variable) => {
    let contractName = variable.contract_name;
    if (!contracts.hasOwnProperty(contractName)) {
      contracts[contractName] = [];
    }
    contracts[contractName].push(variable); // Push the entire variable object
  });

  // Display state variables for each contract
  for (let contractName in contracts) {
    content += `<h4>${contractName}</h4>`;

    contracts[contractName].forEach((variable) => {
      let value = variable.variable_body;
      let variableNameIndex = value.indexOf(variable.variable_name);

      if (variableNameIndex !== -1) {
        let beforeVariableName = value.substring(0, variableNameIndex);
        let afterVariableName = value.substring(
          variableNameIndex + variable.variable_name.length
        );
        value = `<div class="variable-name" data-contract-name="${variable.contract_name}" data-start-line="${variable.line_numbers[0]}" data-end-line="${variable.line_numbers[1]}" style="cursor: pointer; color: #0000a2;">${beforeVariableName}<strong>${variable.variable_name}</strong>${afterVariableName}</div>`;
      }

      content += `<div>${value}</div>`;
    });
  }

  content += "</div>";

  return content;
}

export function createContractDetailDataView(title, dataObject) {
  let content = `<h3>${title}</h3><div>`;
  if (!dataObject) {
    return content + "<div>Not available</div></div>";
  }

  let removeKeys = [
    "all_library_calls",
    "all_solidity_calls",
    "external_calls",
    "all_external_calls",
    "external_addresses_paths",
    "all_reachable_from_functions",
    "all_function_names",
    "all_paths_to_functions",
    "structures_elements",
    "structures_types",
    "structures_with_elements",
    "contract_lines",
    "all_variables",
    "",
  ];

  content += '<div style="margin-bottom: 20px;">';
  if (title == "State Variables") {
    return content + createVariableDataView(dataObject) + "</div>";
  }

  for (let key in dataObject) {
    // Skip if the key is in the array of keys to skip
    if (removeKeys.includes(key) || isEmpty(dataObject[key])) {
      continue;
    }

    let value = dataObject[key];
    if (Array.isArray(value)) {
      value = value.join(", ");
      content += `<div><strong>${key}</strong>: ${value}</div>`;
    } else if (typeof value === "object" && value !== null) {
      value = JSON.stringify(value, null, 2)
        .replace(/\n/g, "<br>")
        .replace(/ /g, "&nbsp;");
      content += `<div><strong>${key}</strong>: ${value}</div>`;
    } else {
      // Handle simple values
      content += `<div><strong>${key}</strong>: ${value}</div>`;
    }
  }
  content += "</div>";

  return content + "</div>";
}

export function formatFunctionData(item) {
  let formattedData = '<div class="data-info">';
  let keyContents = "";
  let expandableButtons = "";

  // Define which keys to display as list or buttons
  const removeKeys = ["priority"];
  const listKeys = ["description"];
  const buttonKeys = [
    "function_full_name",
    "function_body",
    "function_selector",
    "variable_body",
    "variable_type",
    "signature_str",
    "internal_functions",
    "external_calls",
    "modifiers_body",
    "state_vars_read",
    "state_vars_written",
    "all_reachable_from_functions",
    "variables",
    "expressions",
    "high_level_calls",
    "library_level_calls",
    "all_conditional_state_variables_read",
    "prompts",
  ];

  // Define keys that require syntax highlighting
  const syntaxHighlightKeys = [
    "function_body",
    "internal_functions",
    "modifiers_body",
  ];

  for (let key in item) {
    if (removeKeys.includes(key) || !item[key] || isEmpty(item[key])) continue;

    let contentId =
      "content_" + key + "_" + Math.random().toString(36).substr(2, 9);

    if (listKeys.includes(key)) {
      // Add description as listData (server-rendered HTML)
      formattedData += `<div class="list-data">${item[key]}</div>`;
    } else if (buttonKeys.includes(key)) {
      // Prepare expandable buttons HTML
      expandableButtons += `<button class="expandable" data-content-id="${contentId}">${key}</button>`;

      if (key === "prompts") {
        let strategiesContent = `<div class="strategy-buttons-container">`;
        Object.keys(item[key]).forEach((strategy) => {
          strategiesContent += `<button class="strategy-button" data-function-sig="${item.function_full_name}" data-strategy="${strategy}" onclick="generatePrompt('${item.function_full_name}', '${strategy}')">${strategy}</button>`;
        });
        strategiesContent += "</div>";
        keyContents += `<div id="${contentId}" class="key-content" style="display: none;">${strategiesContent}<div class="prompt-data-container"></div></div>`;
      } else {
        let content = Array.isArray(item[key])
          ? item[key].join("<br>")
          : item[key];

        // Syntax highlighting for specific keys
        if (syntaxHighlightKeys.includes(key)) {
          content = unescapeHTML(content);
          content = `<pre><code class="language-solidity">${content}</code></pre>`;
        }

        keyContents += `<div id="${contentId}" class="key-content" style="display: none;">${content}</div>`;
      }
    }
  }

  formattedData += expandableButtons;

  // Append the "Go to Lines" button if line_numbers is available
  if (item.line_numbers) {
    formattedData += `<button class="copy-button goto-lines-button" data-contract-name="${item.contract_name}" data-start-line="${item.line_numbers[0]}" data-end-line="${item.line_numbers[1]}">Go to Lines</button>`;
  }

  // Always add the "Copy" button last
  formattedData += `<button class="copy-button copy-content-button">Copy</button>`;

  formattedData += keyContents;

  formattedData += `</div>`;

  return formattedData;
}

export function gotoLinesInEditor(contractName, startLine, endLine) {
  // Check if the desired contract is already selected
  var select = document
    .getElementById("sourceCodeDisplay")
    .querySelector("select");
  if (select.value !== contractName) {
    // Change the dropdown to the correct contract
    select.value = contractName;
    // Manually trigger the onchange event for the select element
    select.onchange();

    // Wait for the editor to load the new contract's source code
    setTimeout(function () {
      scrollToLines(startLine, endLine);
    }, 100); // Adjust delay as necessary to ensure the source code is loaded
  } else {
    // If the correct contract is already displayed, scroll directly
    scrollToLines(startLine, endLine);
  }
}

export function scrollToLines(startLine, endLine) {
  editor.scrollToLine(startLine, true, true);
  var sourceCodeDisplay = document.getElementById("sourceCodeDisplay");
  var Range = ace.require("ace/range").Range;
  var endColumn = endLine === startLine ? Infinity : 0;
  editor.session.selection.setRange(
    new Range(startLine - 1, 0, endLine - 1, endColumn)
  );
  sourceCodeDisplay.scrollIntoView();
}

export function generatePrompt(functionSig, strategy) {
  const urlParams = new URLSearchParams(window.location.search);
  let session_path = urlParams.get("session_id");
  var sessionData = getSessionData(session_path);
  const functionData = sessionData.functions_data.find(
    (func) => func.function_full_name === functionSig
  );

  if (!functionData) {
    console.error("Function data not found for signature:", functionSig);
    return;
  }

  fetch("/prompt", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      function_data: functionData,
      strategy_for_function: strategy,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      // Find the parent .data-section of the clicked strategy button
      const parentDataSection = document
        .querySelector(
          `button[data-function-sig="${functionSig}"][data-strategy="${strategy}"]`
        )
        .closest(".data-section");
      if (parentDataSection) {
        // Correctly target the .prompt-data-container within this section to insert the prompt
        const promptDataContainer = parentDataSection.querySelector(
          ".prompt-data-container"
        );
        if (promptDataContainer) {
          promptDataContainer.innerHTML = `<div>${data[strategy]}</div>`;
        }
      }
    })
    .catch((error) => {
      console.error("Error generating prompt:", error);
    });
}

export function copyKeyContent() {
  // Find the last active key-content to copy from
  let keyContents = document.querySelectorAll(".key-content.active");
  if (keyContents.length > 0) {
    let activeKeyContent = keyContents[keyContents.length - 1]; // Get the last one that was activated
    // Create a textarea element to help with copying
    let textarea = document.createElement("textarea");
    textarea.value = activeKeyContent.innerText;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  } else {
    alert("No active key content found.");
  }
}
