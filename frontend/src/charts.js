const COLORS = {
  navy:       "#1f2e7a",
  navyLight:  "#8e9ad0",
  teal:       "#158f75",
  tealLight:  "#6dcdb5",
  gridline:   "#d9d9d9",
  textSec:    "#595959",
};

// Compact number: 182000 → "182K", 1250000 → "1.3M"
function compactNumber(n) {
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${(n / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
  if (abs >= 1e3) return `${Math.round(n / 1e3).toLocaleString()}K`;
  return n.toLocaleString();
}

// Format a value according to the chart's unit.
//   "share" / "pct"  → fraction of 1, shown as %   (0.086 → "9%")
//   "percent"        → already percentage points   (34.5 → "35%")
//   "dollars"        → $ prefix, compact           (182000 → "$182K", -12000 → "-$12K")
//   anything else    → thousands separators        (1500 → "1,500")
function formatValue(v, unit) {
  const n = +v;
  if (!isFinite(n)) return v;
  if (unit === "share" || unit === "pct") return `${(n * 100).toFixed(0)}%`;
  if (unit === "percent") return `${n.toFixed(0)}%`;
  if (unit === "dollars") return `${n < 0 ? "-" : ""}$${compactNumber(Math.abs(n))}`;
  return n.toLocaleString();
}

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
  const unit   = chartData.unit;
  const fmt    = v => formatValue(v, unit);

  const x = d3.scaleBand()
    .domain(data.map(d => d[xKey]))
    .range([0, width])
    .padding(0.35);

  const dataMax = d3.max(data, d => +d[yKey]);
  const dataMin = d3.min(data, d => +d[yKey]);
  const yMax = Math.max(dataMax, 0) * 1.15 || 1;   // headroom; never a [0,0] domain
  const yMin = Math.min(dataMin, 0) * 1.15;        // extend below zero only when needed
  const y = d3.scaleLinear().domain([yMin, yMax]).range([height, 0]);
  const yZero = y(0);

  // Gridlines
  g.append("g")
    .attr("class", "grid")
    .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
    .call(ax => ax.select(".domain").remove())
    .call(ax => ax.selectAll("line").attr("stroke", COLORS.gridline).attr("stroke-dasharray", "2,3"));

  // Bars — negative values render below the zero baseline
  g.selectAll(".bar")
    .data(data)
    .join("rect")
    .attr("class", "bar")
    .attr("x", d => x(d[xKey]))
    .attr("y", d => Math.min(y(+d[yKey]), yZero))
    .attr("width", x.bandwidth())
    .attr("height", d => Math.abs(y(+d[yKey]) - yZero))
    .attr("fill", (_, i) => i === 0 ? COLORS.navy : COLORS.tealLight);

  // Data labels — above positive bars, below negative bars
  g.selectAll(".bar-label")
    .data(data)
    .join("text")
    .attr("class", "bar-label")
    .attr("x", d => x(d[xKey]) + x.bandwidth() / 2)
    .attr("y", d => +d[yKey] < 0 ? y(+d[yKey]) + 12 : y(+d[yKey]) - 5)
    .attr("text-anchor", "middle")
    .attr("font-size", "11px")
    .attr("fill", COLORS.textSec)
    .text(d => fmt(+d[yKey]));

  // X axis (category labels stay at the bottom even when bars go negative)
  g.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x).tickSize(0))
    .call(ax => ax.select(".domain").attr("stroke", yMin < 0 ? "none" : COLORS.gridline))
    .call(ax => ax.selectAll("text")
      .attr("font-size", "12px")
      .attr("fill", CO