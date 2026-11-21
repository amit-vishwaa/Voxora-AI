// Dependency-free SVG charts.
import { raw, esc, fmtNum } from "./ui.js";

export function barChart(series, key = "calls", unit = "") {
  const W = 640, H = 210, L = 34, B = 26, T = 12, max = Math.max(4, ...series.map((d) => d[key]));
  const top = Math.ceil(max / 4) * 4, bw = (W - L) / series.length, ph = H - B - T;
  const grid = [0, 1, 2, 3, 4].map((i) => { const y = T + ph - (ph * i) / 4; return `<line class="grid" x1="${L}" x2="${W}" y1="${y}" y2="${y}"/><text x="${L - 6}" y="${y + 4}" text-anchor="end">${fmtNum((top * i) / 4)}</text>`; }).join("");
  const bars = series.map((d, i) => {
    const h = Math.max(d[key] ? 3 : 0, (ph * d[key]) / top), x = L + i * bw + bw * 0.18, y = T + ph - h;
    const label = i % Math.ceil(series.length / 7) === 0 ? `<text x="${x + bw * 0.32}" y="${H - 8}" text-anchor="middle">${new Date(d.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</text>` : "";
    return `<rect class="bar ${i === series.length - 1 ? "today" : ""}" x="${x}" y="${y}" width="${bw * 0.64}" height="${h}" rx="3"><title>${esc(d.date)}: ${d[key]}${unit}</title></rect>${label}`;
  }).join("");
  return raw(`<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart">${grid}${bars}</svg>`);
}

/** Horizontal share bars: items = [{k, n}] */
export function shareBars(items, labels = {}, colors = {}) {
  const total = items.reduce((s, i) => s + i.n, 0) || 1;
  if (!items.length) return raw('<p class="muted small">No data in this period yet.</p>');
  return raw(`<div class="bars">${items.map((i) => `<div class="b"><span>${esc(labels[i.k] || i.k)}</span><span class="meter"><i style="width:${(100 * i.n) / total}%;${colors[i.k] ? `background:${colors[i.k]}` : ""}"></i></span><span class="num right">${i.n}</span></div>`).join("")}</div>`);
}
