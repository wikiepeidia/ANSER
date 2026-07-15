/**
 * helpers.js — Shared utility functions
 * Formatters, storage, CSV export, SVG path builders, Y-axis computation
 */

const Helpers = {
  // --- Number / Currency ---
  formatVND(num) {
    if (typeof num !== "number") num = Number(num) || 0;
    return new Intl.NumberFormat("vi-VN").format(num) + " ₫";
  },
  formatVNDShort(num) {
    if (typeof num !== "number") num = Number(num) || 0;
    if (num >= 1e9) return (num / 1e9).toFixed(1) + "B ₫";
    if (num >= 1e6) return (num / 1e6).toFixed(0) + "M ₫";
    if (num >= 1e3) return (num / 1e3).toFixed(0) + "K ₫";
    return num + " ₫";
  },
  formatNumber(num) {
    return new Intl.NumberFormat("vi-VN").format(num);
  },

  // --- Date / Time ---
  formatDate(date) {
    if (typeof date === "string") date = new Date(date);
    const d = String(date.getDate()).padStart(2, "0");
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const y = date.getFullYear();
    return `${d}/${m}/${y}`;
  },
  formatDateTime(date) {
    if (typeof date === "string") date = new Date(date);
    const time = String(date.getHours()).padStart(2, "0") + ":" + String(date.getMinutes()).padStart(2, "0");
    return `${this.formatDate(date)} ${time}`;
  },
  getDateRange(preset) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    switch (preset) {
      case "7d":
        return { from: new Date(today.getTime() - 6 * 86400000), to: today };
      case "30d":
        return { from: new Date(today.getTime() - 29 * 86400000), to: today };
      case "thisMonth":
        return { from: new Date(now.getFullYear(), now.getMonth(), 1), to: today };
      case "lastMonth": {
        const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const to = new Date(now.getFullYear(), now.getMonth(), 0);
        return { from, to };
      }
      case "thisYear":
        return { from: new Date(now.getFullYear(), 0, 1), to: today };
      case "all":
      default:
        return { from: new Date(2020, 0, 1), to: today };
    }
  },

  // --- LocalStorage ---
  load(key, defaultValue) {
    try {
      const v = localStorage.getItem("anser-" + key);
      return v ? JSON.parse(v) : defaultValue;
    } catch (e) {
      return defaultValue;
    }
  },
  save(key, value) {
    try {
      localStorage.setItem("anser-" + key, JSON.stringify(value));
      return true;
    } catch (e) {
      return false;
    }
  },

  // --- Export CSV ---
  exportCSV(filename, headers, rows) {
    const escape = (v) => {
      if (v === null || v === undefined) return "";
      const s = String(v);
      if (s.includes(",") || s.includes('"') || s.includes("\n")) {
        return '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    };
    const csv = [
      headers.map((h) => escape(h.label)).join(","),
      ...rows.map((r) => headers.map((h) => escape(r[h.key])).join(",")),
    ].join("\n");
    // BOM for Excel UTF-8
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  // --- Export Excel (.xlsx via SheetJS) ---
  exportXLSX(filename, headers, rows, sheetName = "Sheet1") {
    if (typeof XLSX === "undefined") {
      window.showToast?.("Không tải được thư viện Excel, vui lòng thử lại", "error");
      return;
    }
    const aoa = [
      headers.map((h) => h.label),
      ...rows.map((r) => headers.map((h) => (r[h.key] === null || r[h.key] === undefined) ? "" : r[h.key])),
    ];
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    ws["!cols"] = headers.map((h) => ({ wch: Math.max(12, h.label.length + 2) }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
    XLSX.writeFile(wb, filename);
  },

  // --- Download an empty Excel template (header row only) ---
  downloadXLSXTemplate(filename, headers, sheetName = "Mẫu") {
    this.exportXLSX(filename, headers, [], sheetName);
  },

  // --- Read an uploaded Excel file, returns Promise<Array<Array<any>>> (raw rows incl. header) ---
  readXLSXFile(file) {
    return new Promise((resolve, reject) => {
      if (typeof XLSX === "undefined") {
        reject(new Error("Thư viện Excel chưa sẵn sàng"));
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target.result);
          const wb = XLSX.read(data, { type: "array" });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });
          resolve(rows);
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(reader.error || new Error("Không đọc được file"));
      reader.readAsArrayBuffer(file);
    });
  },

  // --- Print ---
  printElement(elementId, title) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const win = window.open("", "_blank", "width=900,height=700");
    if (!win) {
      window.showToast?.("Vui lòng cho phép popup để in báo cáo", "warning");
      return;
    }
    const styles = document.querySelectorAll('link[rel="stylesheet"], style');
    let styleHTML = "";
    styles.forEach((s) => {
      styleHTML += s.outerHTML;
    });
    win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title>${styleHTML}
      <style>
        body { background: #fff !important; padding: 24px; color: #003152; }
        .sidebar, .header, .header__right, .header__left, .noti-panel, .toast, .modal, .report-toolbar { display: none !important; }
        .content { padding: 0 !important; }
        .table-card, .chart-card, .form-card, .alert-card { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #f5f5f5 !important; }
        .stat-card { border: 1px solid #ddd; padding: 12px; }
        .print-header { text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #003152; }
        .print-header h1 { font-size: 20px; color: #003152; margin: 0 0 8px 0; }
        .print-header p { font-size: 12px; color: #64748b; margin: 0; }
      </style>
      </head><body>
      <div class="print-header">
        <h1>${title}</h1>
        <p>ANSER Dashboard · In lúc ${this.formatDateTime(new Date())}</p>
      </div>
      ${el.innerHTML}
      <script>window.onload = function() { setTimeout(function() { window.print(); window.close(); }, 300); };</script>
      </body></html>`);
    win.document.close();
  },

  // --- Table rendering helpers ---
  tableAvatar(code, name, sub) {
    const chipText = (code || "").substring(0, 4).toUpperCase();
    return `
      <div class="table-avatar">
        <div class="table-avatar__chip">${this.escapeHtml(chipText)}</div>
        <div class="table-avatar__info">
          <strong>${this.escapeHtml(name)}</strong>
          ${sub ? `<span>${this.escapeHtml(sub)}</span>` : ""}
        </div>
      </div>
    `;
  },

  trendPill(value, opts = {}) {
    const num = parseFloat(value);
    if (isNaN(num)) return `<span class="muted">${this.escapeHtml(String(value))}</span>`;
    const up = opts.up !== undefined ? opts.up : num >= 0;
    const variant = up ? "up" : "down";
    const sign = num > 0 ? "+" : "";
    const arrow = up ? "up" : "down";
    return `<span class="trend-pill trend-pill--${variant}"><i class="fa-solid fa-arrow-trend-${arrow}"></i> ${sign}${num}%</span>`;
  },

  pill(text, variant, iconClass) {
    return `<span class="pill pill--${variant}">${iconClass ? `<i class="${iconClass}"></i>` : ""} ${this.escapeHtml(text)}</span>`;
  },

  escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  },

  // --- SVG path builders for line charts ---
  buildSmoothPath(points) {
    if (!points || points.length < 2) return "";
    if (points.length === 2) {
      return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
    }
    let d = `M ${this._num(points[0].x)} ${this._num(points[0].y)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i - 1] || points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[i + 2] || points[i + 1];
      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C ${this._num(cp1x)} ${this._num(cp1y)}, ${this._num(cp2x)} ${this._num(cp2y)}, ${this._num(p2.x)} ${this._num(p2.y)}`;
    }
    return d;
  },

  buildAreaPath(points, baselineY = 150) {
    if (!points || points.length < 2) return "";
    const linePath = this.buildSmoothPath(points);
    const last = points[points.length - 1];
    const first = points[0];
    return `${linePath} L ${this._num(last.x)} ${this._num(baselineY)} L ${this._num(first.x)} ${this._num(baselineY)} Z`;
  },

  pointsToAttr(points) {
    if (!points || !points.length) return "";
    return points.map((p) => `${this._num(p.x)},${this._num(p.y)}`).join(";");
  },

  _num(v) {
    return Math.round(v * 100) / 100;
  },

  // --- Y-axis labels for line charts ---
  computeYAxis(valuesArr, count = 5) {
    const all = (valuesArr || []).flat().filter((v) => typeof v === "number" && !isNaN(v));
    if (!all.length) return { labels: [], min: 0, max: 100, format: (v) => String(v) };
    let min = Math.min(...all);
    let max = Math.max(...all);
    if (min === max) {
      min = min * 0.9;
      max = max * 1.1 || 10;
    }
    const range = max - min;
    const rawStep = range / (count - 1);
    const step = this._niceNumber(rawStep);
    const niceMin = Math.floor(min / step) * step;
    const niceMax = Math.ceil(max / step) * step;
    const labels = [];
    for (let v = niceMax; v >= niceMin - step / 2; v -= step) {
      if (v < niceMin - 1e-9) break;
      labels.push(Math.max(niceMin, v));
    }
    const format = (v) => this.formatVNDShort(v);
    return { labels, min: niceMin, max: niceMax, step, format };
  },

  _niceNumber(x) {
    if (x <= 0) return 1;
    const exp = Math.floor(Math.log10(x));
    const f = x / Math.pow(10, exp);
    let niceF;
    if (f < 1.5) niceF = 1;
    else if (f < 3) niceF = 2;
    else if (f < 7) niceF = 5;
    else niceF = 10;
    return niceF * Math.pow(10, exp);
  },

  renderYAxis(valuesArr, opts = {}) {
    const { labels, format } = this.computeYAxis(valuesArr, opts.count || 5);
    if (!labels.length) return "";
    return `<div class="line-chart__y-axis">${labels
      .map((v, i) => {
        const top = (i / (labels.length - 1)) * 100;
        return `<span style="top: ${top.toFixed(1)}%">${format(v)}</span>`;
      })
      .join("")}</div>`;
  },

  // --- Line chart hover: crosshair + tooltip showing values on mousemove ---
  // svg: the <svg> element containing the line/area path (with a viewBox)
  // opts.points: [{x,y}, ...] in SVG viewBox coordinates
  // opts.values: raw values aligned with points, used for the tooltip text
  // opts.labels: labels aligned with points, shown as the tooltip header
  // opts.seriesName / opts.color: legend text + dot color in the tooltip row
  // opts.formatValue: (value) => string
  initLineChartHover(svg, opts) {
    const container = (opts && opts.container) || svg.closest(".line-chart");
    if (!container || !opts || !opts.points || !opts.points.length) return;
    const vb = svg.viewBox.baseVal;
    const vbW = vb && vb.width ? vb.width : 400;
    const vbH = vb && vb.height ? vb.height : 150;
    const ns = "http://www.w3.org/2000/svg";
    const points = opts.points;
    const values = opts.values || points.map((p) => p.y);
    const labels = opts.labels || [];
    const color = opts.color || "var(--brand-primary)";
    const formatValue = opts.formatValue || ((v) => String(v));

    const rect = document.createElementNS(ns, "rect");
    rect.setAttribute("class", "line-chart__hover-rect");
    rect.setAttribute("x", "0");
    rect.setAttribute("y", "0");
    rect.setAttribute("width", String(vbW));
    rect.setAttribute("height", String(vbH));
    svg.appendChild(rect);

    const guide = document.createElementNS(ns, "line");
    guide.setAttribute("class", "line-chart__guide");
    guide.setAttribute("y1", "0");
    guide.setAttribute("y2", String(vbH));
    guide.setAttribute("stroke", "var(--chart-bar-bg)");
    guide.setAttribute("stroke-width", "1");
    guide.setAttribute("opacity", "0");
    svg.appendChild(guide);

    const pointOuter = document.createElementNS(ns, "circle");
    pointOuter.setAttribute("class", "line-chart__point");
    pointOuter.setAttribute("r", "5");
    pointOuter.setAttribute("fill", "var(--bg-card)");
    pointOuter.setAttribute("stroke", color);
    pointOuter.setAttribute("stroke-width", "2");
    pointOuter.setAttribute("opacity", "0");
    svg.appendChild(pointOuter);

    const pointInner = document.createElementNS(ns, "circle");
    pointInner.setAttribute("class", "line-chart__point-inner");
    pointInner.setAttribute("r", "2");
    pointInner.setAttribute("fill", color);
    pointInner.setAttribute("opacity", "0");
    svg.appendChild(pointInner);

    let tooltip = container.querySelector(".line-chart__tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "line-chart__tooltip";
      container.appendChild(tooltip);
    }
    tooltip.hidden = true;

    const showAt = (index) => {
      const p = points[index];
      if (!p) return;
      guide.setAttribute("x1", String(p.x));
      guide.setAttribute("x2", String(p.x));
      guide.setAttribute("opacity", "1");
      pointOuter.setAttribute("cx", String(p.x));
      pointOuter.setAttribute("cy", String(p.y));
      pointOuter.setAttribute("opacity", "1");
      pointInner.setAttribute("cx", String(p.x));
      pointInner.setAttribute("cy", String(p.y));
      pointInner.setAttribute("opacity", "1");

      tooltip.innerHTML = `
        ${labels[index] ? `<span class="line-chart__tooltip-label">${this.escapeHtml(labels[index])}</span>` : ""}
        <div class="line-chart__tooltip-rows">
          <div class="line-chart__tooltip-row">
            <span class="line-chart__tooltip-dot" style="background:${color}"></span>
            <span class="line-chart__tooltip-name">${this.escapeHtml(opts.seriesName || "")}</span>
            <span class="line-chart__tooltip-val">${formatValue(values[index])}</span>
          </div>
        </div>
      `;
      tooltip.hidden = false;

      const svgRect = svg.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const scaleX = svgRect.width / vbW;
      const scaleY = svgRect.height / vbH;
      const pxX = svgRect.left - containerRect.left + p.x * scaleX;
      const pxY = svgRect.top - containerRect.top + p.y * scaleY;
      let left = pxX;
      const half = tooltip.offsetWidth / 2;
      const maxLeft = container.clientWidth - half;
      left = Math.min(Math.max(half, left), Math.max(half, maxLeft));
      tooltip.style.left = `${left}px`;
      let top = pxY - tooltip.offsetHeight - 14;
      if (top < 0) top = pxY + 14;
      tooltip.style.top = `${top}px`;
    };

    const hide = () => {
      guide.setAttribute("opacity", "0");
      pointOuter.setAttribute("opacity", "0");
      pointInner.setAttribute("opacity", "0");
      tooltip.hidden = true;
    };

    rect.addEventListener("mousemove", (e) => {
      const svgRect = svg.getBoundingClientRect();
      const relX = ((e.clientX - svgRect.left) / svgRect.width) * vbW;
      let nearest = 0;
      let minDist = Infinity;
      points.forEach((p, i) => {
        const d = Math.abs(p.x - relX);
        if (d < minDist) {
          minDist = d;
          nearest = i;
        }
      });
      showAt(nearest);
    });
    rect.addEventListener("mouseleave", hide);
  },
};

// --- Standalone greeting helpers (used by Home page) ---
function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 11) return "Chào buổi sáng";
  if (hour < 14) return "Chào buổi trưa";
  if (hour < 18) return "Chào buổi chiều";
  return "Chào buổi tối";
}

function getFormattedDate() {
  const days = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
  const now = new Date();
  const day = days[now.getDay()];
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yyyy = now.getFullYear();
  return `${day}, ${dd}/${mm}/${yyyy}`;
}

// Expose for inline use
window.getGreeting = getGreeting;
window.getFormattedDate = getFormattedDate;

// Expose to window for inline onclick handlers in templates
window.Helpers = Helpers;