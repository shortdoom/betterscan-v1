const targetAddress = getTargetAddressFromURL();

export function createProtocolMap(target_div = "#dashboard") {
  const dashboard = document.getElementById("dashboard");
  const width = dashboard.offsetWidth;
  let height = window.innerHeight;
  let foldedHeight = 45;
  let isFolded = false;

  fetch("/protocol_view")
    .then((response) => response.json())
    .then((data) => {
      const nodes = data.nodes;
      const links = data.links;

      const connectedNodeIds = new Set(
        links.flatMap((link) => [link.source, link.target])
      );

      nodes.forEach((node) => {
        node.connected = connectedNodeIds.has(node.id);
      });

      const svg = d3
        .select(target_div)
        .append("svg")
        .attr("class", "network-svg")
        .attr("width", width)
        .attr("height", height);

      svg
        .append("defs")
        .append("marker")
        .attr("id", "arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 25)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto-start-reverse")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#000");

      svg
        .append("text")
        .text("Protocol View")
        .attr("x", 20)
        .attr("y", 30)
        .attr("font-family", "monospace")
        .attr("font-weight", "bold")
        .attr("opacity", 0.7)
        .attr("font-size", 16);

      const toggleGroup = svg
        .append("g")
        .attr("class", "toggle-button")
        .style("cursor", "pointer")
        .attr("transform", `translate(${width - 150}, 10)`);
      toggleGroup
        .append("rect")
        .attr("width", 90)
        .attr("height", 20)
        .attr("fill", "white")
        .attr("stroke", "#333")
        .attr("stroke-width", 2);
      toggleGroup
        .append("text")
        .attr("x", 45)
        .attr("y", 15)
        .attr("text-anchor", "middle")
        .text("HideView")
        .on("click", () => {
          isFolded = !isFolded;
          svg.attr("height", isFolded ? foldedHeight : height);
          d3.select(this).text(isFolded ? "ExpandView" : "HideView");
        });

      const simulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(150)
        )
        .force("charge", d3.forceManyBody().strength(-500))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force(
          "radial",
          d3
            .forceRadial((d) => (d.connected ? 0 : 150), width / 2, height / 2)
            .strength((d) => (d.connected ? 0 : 0.1))
        );

      const tooltip = d3
        .select("body")
        .append("div")
        .attr("class", "tooltip")
        .style("position", "absolute")
        .style("background", "white")
        .style("padding", "10px")
        .style("border", "1px solid #ccc")
        .style("border-radius", "5px")
        .style("visibility", "hidden");

      const link = svg
        .append("g")
        .attr("stroke", "blue")
        .attr("stroke-opacity", 0.5)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", 2)
        .attr("marker-end", "url(#arrow)");

      const node = svg
        .append("g")
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", 10)
        .attr("fill", (d) => {
          if (d.address === targetAddress) {
            return "green"; // Active Contract
          } else if (d.label === "ZERO_ADDRESS") {
            return "black"; // Zero address special case
          } else if (d.core_periphery === "core") {
            return "blue"; // Core node color
          } else if (d.core_periphery === "periphery") {
            return "grey"; // Periphery node color
            // } else if (d.k_crust) {
            //   return "purple";  // Crust node color
            // } else if (d.k_shell) {
            //   return "blue";  // Shell node color
            // } else if (d.k_corona) {
            //   return "black";  // Corona node color
          } else {
            // Color by strongly connected component
            return d.connected ? "red" : "white";
          }
        })
        .call(drag(simulation))
        .on("click", function (event, d) {
          const expressionsFormatted = d.ext_expressions
            .map((expr) => `<li>${expr}</li>`)
            .join("");
          const sessionUrl = `/?session_id=${d.session_path
            .split("/")
            .pop()
            .replace(/:/g, ":")}`;
          tooltip
            .html(
              `<strong>Address:</strong> ${d.address}<br><strong>Calls made:</strong> <ul>${expressionsFormatted}</ul><strong>Session:</strong> <a href='${sessionUrl}' style='text-decoration: underline; color: blue;'>Open Session</a>`
            )
            .style("visibility", "visible")
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY + 10}px`);
        });

      const labels = svg
        .append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .text((d) => d.label)
        .attr("x", 15)
        .attr("y", "0.31em")
        .attr("font-family", "monospace")
        .attr("font-weight", "bold")
        .attr("font-size", 14)
        .attr("fill", "black");

      svg.on("click", function (event) {
        if (event.target.tagName === "svg") {
          tooltip.style("visibility", "hidden");
        }
      });

      simulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);
        node
          .each((d) => {
            d.x = Math.max(15, Math.min(width - 15, d.x));
            d.y = Math.max(15, Math.min(height - 15, d.y));
          })
          .attr("cx", (d) => d.x)
          .attr("cy", (d) => d.y);
        labels.attr("x", (d) => d.x + 20).attr("y", (d) => d.y + 15);
        let maxY = Math.max(...node.data().map((d) => d.y + 15));
        let minY = Math.min(...node.data().map((d) => d.y - 15));
        const neededHeight = maxY - minY + 30;
        if (neededHeight > height) {
          height = neededHeight;
          svg.attr("height", height);
          simulation
            .force("center", d3.forceCenter(width / 2, height / 2))
            .alpha(0.3)
            .restart();
        }
      });

      addLegend(svg);

      function drag(simulation) {
        return d3
          .drag()
          .on("start", function (event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          })
          .on("drag", function (event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          })
          .on("end", function (event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
          });
      }
    })
    .catch(function (error) {
      console.error("Error fetching data:", error);
    });
}

export function createProtocolAnalysis(target_div = "#protocolAnalysis") {
  const analysisContainer = document.getElementById(target_div.slice(1)); // Assuming # is included in target_div

  fetch("/protocol_analysis")
    .then((response) => response.json())
    .then((components) => {
      // Clear previous contents
      analysisContainer.innerHTML = "";

      // Iterate over each component and create a force-directed graph
      components.forEach((data, index) => {
        const nodes = data.nodes;
        const links = data.links;

        if (nodes.length > 0 && links.length > 0) {
          const componentDiv = document.createElement("div");
          componentDiv.className = "component";
          analysisContainer.appendChild(componentDiv);

          const svg = d3
            .select(componentDiv)
            .append("svg")
            .attr("class", "network-svg")
            .attr("width", "100%")
            .attr("height", 300); // Static height, adjust as needed

          const simulation = d3
            .forceSimulation(nodes)
            .force(
              "link",
              d3
                .forceLink(links)
                .id((d) => d.id)
                .distance(50)
            )
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(componentDiv.clientWidth / 2, 150));

          const link = svg
            .append("g")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke-width", (d) => Math.sqrt(d.value));

          const node = svg
            .append("g")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .selectAll("circle")
            .data(nodes)
            .join("circle")
            .attr("r", 5)
            .attr("fill", colorByGroup)
            .call(drag(simulation));

          node.append("title").text((d) => d.id);

          simulation.on("tick", () => {
            link
              .attr("x1", (d) => d.source.x)
              .attr("y1", (d) => d.source.y)
              .attr("x2", (d) => d.target.x)
              .attr("y2", (d) => d.target.y);

            node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
          });
        }
      });
    })
    .catch(function (error) {
      console.error("Error fetching data:", error);
    });

  function drag(simulation) {
    return d3
      .drag()
      .on("start", function (event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", function (event, d) {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", function (event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
  }

  function colorByGroup(d) {
    // Example coloring function, define your own logic
    return d.group ? colorScale(d.group) : "#ccc";
  }
}

function addLegend(svg) {
  const svgHeight = window.innerHeight;
  const startingYPosition = svgHeight - 220;

  const legend = svg
    .append("g")
    .attr("class", "legend")
    .attr("transform", `translate(10, ${startingYPosition})`);

  const nodeColors = [
    { color: "red", text: "Smart Contract" },
    { color: "white", text: "Library / Interface" },
    { color: "blue", text: "Core Contracts" },
    { color: "green", text: "Active Contract" },
  ];

  // Positioning the nodes and their labels
  const nodeLegend = legend
    .selectAll(".node-legend")
    .data(nodeColors)
    .enter()
    .append("g")
    .attr("class", "node-legend")
    .attr("transform", (d, i) => `translate(0, ${i * 25})`);

  nodeLegend
    .append("circle")
    .attr("r", 10)
    .attr("fill", (d) => d.color)
    .attr("cx", 15);

  nodeLegend
    .append("text")
    .attr("x", 35)
    .attr("y", 5)
    .text((d) => d.text)
    .attr("font-family", "monospace")
    .attr("font-size", 14);

  // Adjusted y positions for the arrows and link information
  const additionalElementsStartY = nodeColors.length * 25 + 20;

  legend
    .append("text")
    .attr("x", 0)
    .attr("y", additionalElementsStartY)
    .text("Arrow shows the direction of the call")
    .attr("font-family", "monospace")
    .attr("font-size", 14);

  legend
    .append("line")
    .attr("x1", 0)
    .attr("y1", additionalElementsStartY + 10)
    .attr("x2", 30)
    .attr("y2", additionalElementsStartY + 10)
    .attr("stroke", "black")
    .attr("stroke-width", 2)
    .attr("marker-end", "url(#arrow)");

  legend
    .append("text")
    .attr("x", 0)
    .attr("y", additionalElementsStartY + 40)
    .text("Link represents an external call between contracts")
    .attr("font-family", "monospace")
    .attr("font-size", 14);

  legend
    .append("line")
    .attr("x1", 0)
    .attr("y1", additionalElementsStartY + 50)
    .attr("x2", 30)
    .attr("y2", additionalElementsStartY + 50)
    .attr("stroke", "blue")
    .attr("stroke-width", 2);

  legend
    .append("text")
    .attr("x", 0)
    .attr("y", additionalElementsStartY + 70)
    .text("Click on a node to see more details")
    .attr("font-family", "monospace")
    .attr("font-size", 14);
}

function getTargetAddressFromURL() {
  const queryParams = new URLSearchParams(window.location.search);
  const sessionId = queryParams.get("session_id");
  if (sessionId) {
    const parts = sessionId.split(":");
    return parts.length > 1 ? parts[1] : null;
  }
  return null;
}
