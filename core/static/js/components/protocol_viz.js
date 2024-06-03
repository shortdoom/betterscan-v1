export function createProtocolMap(target_div = "#dashboard") {
  const dashboard = document.getElementById("dashboard");
  const width = dashboard.offsetWidth;
  let height = window.innerHeight;

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
        .attr("fill", (d) => (d.connected ? "red" : "white"))
        .call(drag(simulation))
        .on("click", function (event, d) {
          // Display the additional info when a node is clicked
          tooltip
            .html("address: " + d.address)
            .style("visibility", "visible")
            .style("left", event.pageX + 10 + "px")
            .style("top", event.pageY + 10 + "px");
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
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", "translate(10, 10)"); // Positioning the legend on the SVG
  
    // Adding legend for node colors
    const nodeColors = [
      { color: "red", text: "Smart Contract" },
      { color: "white", text: "Library" }
    ];
  
    const nodeLegend = legend.selectAll(".node-legend")
      .data(nodeColors)
      .enter().append("g")
      .attr("class", "node-legend")
      .attr("transform", (d, i) => `translate(0, ${i * 25 + 10})`);  // Adjust vertical spacing between items
  
    nodeLegend.append("circle")
      .attr("r", 10)
      .attr("fill", d => d.color)
      .attr("cx", 15); // Adjust circle x position to align with other elements
  
    nodeLegend.append("text")
      .attr("x", 35) // Adjusting the text position to the right of the circle for better alignment
      .attr("y", 5) // Aligning text in the middle of the circle
      .text(d => d.text)
      .attr("font-family", "monospace")
      .attr("font-size", 14);
  
    // Adding legend for the arrows
    legend.append("text")
      .attr("x", 0)
      .attr("y", 60)
      .text("Arrow shows the direction of the call")
      .attr("font-family", "monospace")
      .attr("font-size", 14);
  
    legend.append("line")
      .attr("x1", 0)
      .attr("y1", 70)
      .attr("x2", 30)
      .attr("y2", 70)
      .attr("stroke", "black")
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrow)"); // Using the same arrow marker
  
    // Adding legend for the line representing external calls without arrows
    legend.append("text")
      .attr("x", 0)
      .attr("y", 90)
      .text("Link represents an external call between contracts")
      .attr("font-family", "monospace")
      .attr("font-size", 14);
  
    legend.append("line")
      .attr("x1", 0)
      .attr("y1", 100)
      .attr("x2", 30)
      .attr("y2", 100)
      .attr("stroke", "blue")
      .attr("stroke-width", 2); // Regular line without arrow


    // Adding legend for the arrows
    legend.append("text")
      .attr("x", 0)
      .attr("y", 120)
      .text("Click on a node to see more details")
      .attr("font-family", "monospace")
      .attr("font-size", 14);
  }
  