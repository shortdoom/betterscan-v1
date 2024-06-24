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

      const svgTitle = svg
        .append("text")
        .text("Protocol View")
        .attr("x", 20)
        .attr("y", 30)
        .attr("font-family", "monospace")
        .attr("font-weight", "bold")
        .attr("opacity", 0.7)
        .attr("font-size", 16);

      // Toggle button in SVG
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

      const toggleText = toggleGroup
        .append("text")
        .attr("x", 45)
        .attr("y", 15)
        .attr("text-anchor", "middle")
        .text("HideView");

        toggleGroup.on("click", () => {
          if (!isFolded) {
            svg.attr("height", foldedHeight);
            toggleText.text("ExpandView");
            isFolded = true;
          } else {
            svg.attr("height", height);
            toggleText.text("HideView");
            isFolded = false;
          }
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
        .force(
          "charge",
          d3.forceManyBody().strength((d) => -500)
        )
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
        .style("visibility", "hidden"); // initially hidden

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
            return "green"; // Color the node green if it matches the address in the URL
          } else if (d.label === "ZERO_ADDRESS") {
            return "grey";
          } else {
            return d.connected ? "red" : "white";
          }
        })
        .call(drag(simulation))
        .on("click", function (event, d) {
          let session_id = d.session_path.split("/").pop();
          session_id = session_id.split(":"); 
          session_id = `${session_id[0]}:${session_id[1]}`; 
          
          const expressionsFormatted = d.ext_expressions
            .map((expr) => `<li>${expr}</li>`)
            .join("");

          const sessionUrl = `/?session_id=${session_id}`;

          tooltip
            .html(
              `<strong>Address:</strong> ${d.address}<br>
                   <strong>Calls made:</strong> <ul>${expressionsFormatted}</ul>
                   <strong>Session:</strong> <a href='${sessionUrl}' style='text-decoration: underline; color: blue;'>Open Session</a>`
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

      // Hide the tooltip when clicking anywhere else on the SVG
      svg.on("click", function (event) {
        if (event.target.tagName === "svg") {
          tooltip.style("visibility", "hidden");
        }
      });

      simulation.on("tick", () => {
        let maxY = 0;
        let minY = Infinity;
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node
          .each(function (d) {
            d.x = Math.max(15, Math.min(width - 15, d.x));
            d.y = Math.max(15, Math.min(height - 15, d.y));
          })
          .attr("cx", (d) => d.x)
          .attr("cy", (d) => d.y);

        labels.attr("x", (d) => d.x + 20).attr("y", (d) => d.y + 15);

        maxY = Math.max(maxY, ...node.data().map((d) => d.y + 15));
        minY = Math.min(minY, ...node.data().map((d) => d.y - 15));
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

function addLegend(svg) {
  const svgHeight = window.innerHeight;

  // Calculate the starting Y position of the legend dynamically to move it sufficiently up
  const startingYPosition = svgHeight - 220; // Adjusted to move up the entire legend

  const legend = svg
    .append("g")
    .attr("class", "legend")
    .attr("transform", `translate(10, ${startingYPosition})`);

  const nodeColors = [
    { color: "red", text: "Smart Contract" },
    { color: "white", text: "Library / Interface" },
    { color: "grey", text: "ZERO_ADDRESS" },
    { color: "green", text: "Active Contract" } // Added new entry for Active Contract
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
    .attr("stroke-width", 2); // Regular line without arrow

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
    const parts = sessionId.split(':');
    return parts.length > 1 ? parts[1] : null; // Assuming the address is after the first colon
  }
  return null;
}
