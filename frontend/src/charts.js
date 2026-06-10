const COLORS = {
  navy:       "#1f2e7a",
  navyLight:  "#8e9ad0",
  teal:       "#158f75",
  tealLight:  "#6dcdb5",
  gridline:   "#d9d9d9",
  textSec:    "#595959",
};

function renderBarChart(svgEl, chartData) {
  const svg = d3.select(svgEl);
  svg.selectAll("*").remove();

  const margin = { top: 8, right: 24, bottom: 60, left: 56 };
  const width  = svgEl.getBoundingClientRect().width - margin.left - margin.right;
  const height = svgEl.getBoundingClientRect().height - margin.top - margin.bottom;

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const data   = chartData.data;
  const xKey   = chartData.x_key;
  const yKey   = chartData.y_key;
  const isPercent = chartData.unit === "share" || chartData.unit === "pct";

  const x = d3.scaleBand()
    .domain(data.map(d => d[xKey]))
    .range([0, width])
    .padding(0.35);

  const yMax = d3.max(data, d => +d[yKey]) * 1.15;
  const y = d3.scaleLinear().domain([0, yMax]).range([height, 0]);

  // Gridlines
  g.append("g")
    .attr("class", "grid")
    .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
    .call(ax => ax.select(".domain").remove())
    .call(ax => ax.selectAll("line").attr("stroke", COLORS.gridline).attr("stroke-dasharray", "2,3"));

  // Bars
  g.selectAll(".bar")
    .data(data)
    .join("rect")
    .attr("class", "bar")
    .attr("x", d => x(d[xKey]))
    .attr("y", d => y(+d[yKey]))
    .attr("width", x.bandwidth())
    .attr("height", d => height - y(+d[yKey]))
    .attr("fill", (_, i) => i === 0 ? COLORS.navy : COLORS.tealLight);

  // Data labels
  g.selectAll(".bar-label")
    .data(data)
    .join("text")
    .attr("class", "bar-label")
    .attr("x", d => x(d[xKey]) + x.bandwidth() / 2)
    .attr("y", d => y(+d[yKey]) - 5)
    .attr("text-anchor", "middle")
    .attr("font-size", "11px")
    .attr("fill", COLORS.textSec)
    .text(d => isPercent ? `${(+d[yKey] * 100).toFixed(0)}%` : d[yKey]);

  // X axis
  g.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x).tickSize(0))
    .call(ax => ax.select(".domain").attr("stroke", COLORS.gridline))
    .call(ax => ax.selectAll("text")
      .attr("font-size", "12px")
      .attr("fill", COLORS.textSec)
      .attr("dy", "1.2em")
      .call(wrap, x.bandwidth() + x.step() * x.paddingInner()));

  // Y axis
  g.append("g")
    .call(d3.axisLeft(y).ticks(5).tickFormat(v => isPercent ? `${(v * 100).toFixed(0)}%` : v))
    .call(ax => ax.select(".domain").remove())
    .call(ax => ax.selectAll("text").attr("font-size", "11px").attr("fill", COLORS.textSec));
}

// Wrap long axis labels
function wrap(selection, maxWidth) {
  selection.each(function () {
    const text = d3.select(this);
    const words = text.text().split(/\s+/).reverse();
    let word, line = [], lineNumber = 0;
    const lineHeight = 1.1;
    const y = text.attr("y");
    const dy = parseFloat(text.attr("dy")) || 0;
    let tspan = text.text(null).append("tspan").attr("x", 0).attr("y", y).attr("dy", `${dy}em`);

    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > maxWidth) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan")
          .attr("x", 0).attr("y", y)
          .attr("dy", `${++lineNumber * lineHeight + dy}em`)
          .text(word);
      }
    }
  });
}

function renderChart(svgEl, chartData) {
  if (!chartData || !chartData.data?.length) return;
  if (chartData.type === "bar") renderBarChart(svgEl, chartData);
}

window.QECharts = { renderChart };
