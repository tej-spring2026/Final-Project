/**
 * charts.js — Options Strategy Builder client-side logic
 *
 * Depends on: TICKER, SPOT, EXPIRATIONS (injected by builder.html)
 * Requires:   Plotly (CDN), Bootstrap 5 (CDN)
 */

// ─── Application state ──────────────────────────────────────────────────────
const state = {
  ticker:     TICKER,
  spot:       SPOT,
  expiration: null,
  legs: [],  // [{option_type, strike, expiration, quantity, entry_price, label}]
};


// ─── Bootstrap init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("expiration-select");
  sel.addEventListener("change", () => loadChain(sel.value));
  if (sel.options.length > 0) loadChain(sel.value);
});


// ─── Chain loading ──────────────────────────────────────────────────────────

async function loadChain(expiration) {
  state.expiration = expiration;
  _show("chain-loading");
  _hide("chain-container");
  _hide("chain-error");

  try {
    const resp = await fetch(
      `/api/chain?ticker=${encodeURIComponent(state.ticker)}&expiration=${encodeURIComponent(expiration)}`
    );
    const data = await resp.json();
    if (data.error) throw new Error(data.error);

    state.spot = data.spot;
    document.getElementById("spot-display").textContent = `$${data.spot.toFixed(2)}`;
    renderChainTable(data.contracts);

    _hide("chain-loading");
    _show("chain-container");
  } catch (err) {
    _hide("chain-loading");
    const el = document.getElementById("chain-error");
    el.textContent = `Could not load chain: ${err.message}`;
    _show("chain-error");
  }
}

function renderChainTable(contracts) {
  // Separate into calls / puts keyed by strike
  const calls = {}, puts = {};
  contracts.forEach(c => {
    if (c.option_type === "call") calls[c.strike] = c;
    else                          puts[c.strike]  = c;
  });

  const allStrikes = [...new Set(contracts.map(c => c.strike))].sort((a, b) => a - b);

  // Find the ATM strike (closest to spot)
  const atmStrike = allStrikes.reduce((prev, cur) =>
    Math.abs(cur - state.spot) < Math.abs(prev - state.spot) ? cur : prev
  );

  const tbody = document.getElementById("chain-body");
  tbody.innerHTML = "";

  allStrikes.forEach(strike => {
    const call = calls[strike];
    const put  = puts[strike];
    const isAtm = strike === atmStrike;

    const tr = document.createElement("tr");
    if (isAtm) tr.className = "atm-row";

    tr.innerHTML =
      _callCells(call, strike) +
      `<td class="text-center strike-col fw-bold ${isAtm ? "text-warning" : ""}">${strike}</td>` +
      _putCells(put, strike);

    tbody.appendChild(tr);
  });

  // Scroll to ATM row
  const rows = tbody.querySelectorAll("tr");
  const atmIdx = allStrikes.indexOf(atmStrike);
  if (rows[atmIdx]) rows[atmIdx].scrollIntoView({ block: "center", behavior: "smooth" });
}

function _callCells(c, strike) {
  if (!c) return '<td colspan="4" class="text-muted text-end border-end">—</td>';
  const iv    = c.iv    != null ? `${c.iv}%`            : "—";
  const delta = c.delta != null ? c.delta.toFixed(2)    : "—";
  const mid   = c.mid   > 0    ? `$${c.mid.toFixed(2)}` : "—";
  const btns  = c.mid > 0
    ? `<button class="btn btn-xs btn-success"  onclick="addLeg('call',${strike},'${c.expiration}',${c.mid},'${c.symbol}',1)">L</button>
       <button class="btn btn-xs btn-danger ms-1" onclick="addLeg('call',${strike},'${c.expiration}',${c.mid},'${c.symbol}',-1)">S</button>`
    : '<span class="text-muted small">—</span>';
  return `<td class="text-end small text-muted">${iv}</td>
          <td class="text-end small">${delta}</td>
          <td class="text-end small">${mid}</td>
          <td class="text-center border-end">${btns}</td>`;
}

function _putCells(c, strike) {
  if (!c) return '<td colspan="4" class="text-muted text-start border-start">—</td>';
  const iv    = c.iv    != null ? `${c.iv}%`            : "—";
  const delta = c.delta != null ? c.delta.toFixed(2)    : "—";
  const mid   = c.mid   > 0    ? `$${c.mid.toFixed(2)}` : "—";
  const btns  = c.mid > 0
    ? `<button class="btn btn-xs btn-success"  onclick="addLeg('put',${strike},'${c.expiration}',${c.mid},'${c.symbol}',1)">L</button>
       <button class="btn btn-xs btn-danger ms-1" onclick="addLeg('put',${strike},'${c.expiration}',${c.mid},'${c.symbol}',-1)">S</button>`
    : '<span class="text-muted small">—</span>';
  return `<td class="text-center border-start">${btns}</td>
          <td class="text-start small">${mid}</td>
          <td class="text-start small text-muted">${iv}</td>
          <td class="text-start small">${delta}</td>`;
}


// ─── Leg management ─────────────────────────────────────────────────────────

function addLeg(optionType, strike, expiration, entryPrice, symbol, qty) {
  const label = `${optionType.toUpperCase()} K=${strike} @ $${entryPrice.toFixed(2)} (${expiration})`;
  state.legs.push({ option_type: optionType, strike, expiration, quantity: qty, entry_price: entryPrice, label });
  renderLegsPanel();
  refreshChart();
}

function removeLeg(idx) {
  state.legs.splice(idx, 1);
  renderLegsPanel();
  refreshChart();
}

function toggleSide(idx) {
  state.legs[idx].quantity *= -1;
  renderLegsPanel();
  refreshChart();
}

function changeAbsQty(idx, delta) {
  const leg = state.legs[idx];
  const sign = leg.quantity >= 0 ? 1 : -1;
  const newAbs = Math.max(1, Math.abs(leg.quantity) + delta);
  leg.quantity = sign * newAbs;
  renderLegsPanel();
  refreshChart();
}

function setAbsQty(idx, val) {
  const leg = state.legs[idx];
  const sign = leg.quantity >= 0 ? 1 : -1;
  const abs = Math.max(1, Math.min(10, parseInt(val) || 1));
  leg.quantity = sign * abs;
  renderLegsPanel();
  refreshChart();
}

function clearLegs() {
  state.legs = [];
  renderLegsPanel();
  refreshChart();
}

function renderLegsPanel() {
  const emptyEl = document.getElementById("legs-empty");
  const listEl  = document.getElementById("legs-list");

  if (state.legs.length === 0) {
    emptyEl.classList.remove("d-none");
    listEl.innerHTML = "";
    return;
  }
  emptyEl.classList.add("d-none");

  listEl.innerHTML = state.legs.map((leg, idx) => {
    const isLong   = leg.quantity > 0;
    const absQty   = Math.abs(leg.quantity);
    const badgeCls = isLong ? "bg-success" : "bg-danger";
    const sideLabel = isLong ? "LONG" : "SHORT";
    return `
      <div class="leg-item d-flex align-items-center gap-2 mb-2 p-2 rounded">
        <button class="btn btn-xs ${isLong ? "btn-success" : "btn-danger"} leg-side-btn"
                onclick="toggleSide(${idx})" title="Toggle Long/Short">
          ${sideLabel}
        </button>
        <span class="small flex-grow-1 text-truncate leg-label" title="${leg.label}">
          ${leg.option_type.toUpperCase()} K=${leg.strike}
          <span class="text-muted">@ $${leg.entry_price.toFixed(2)}</span>
        </span>
        <div class="input-group input-group-sm qty-group">
          <button class="btn btn-outline-secondary btn-xs" onclick="changeAbsQty(${idx},-1)">−</button>
          <input type="number" class="form-control text-center p-0 qty-input"
                 value="${absQty}" min="1" max="10"
                 onchange="setAbsQty(${idx}, this.value)">
          <button class="btn btn-outline-secondary btn-xs" onclick="changeAbsQty(${idx},1)">+</button>
        </div>
        <button class="btn btn-xs btn-outline-danger" onclick="removeLeg(${idx})" title="Remove leg">✕</button>
      </div>`;
  }).join("");
}


// ─── Chart + metrics ────────────────────────────────────────────────────────

async function refreshChart() {
  if (state.legs.length === 0) {
    _show("chart-placeholder");
    _hideel(document.getElementById("chart"));
    document.getElementById("metrics-card").style.display = "none";
    Plotly.purge("chart");
    return;
  }

  try {
    const resp = await fetch("/api/payoff", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ legs: state.legs, spot: state.spot }),
    });
    const data = await resp.json();
    if (data.error) { console.error("Payoff error:", data.error); return; }

    _hide("chart-placeholder");
    const chartEl = document.getElementById("chart");
    chartEl.style.display = "";
    document.getElementById("metrics-card").style.display = "";

    renderChart(data);
    renderMetrics(data);
  } catch (err) {
    console.error("refreshChart:", err);
  }
}

function renderChart(data) {
  const prices = data.price_range;
  const pnl    = data.pnl;

  const yMin = Math.min(...pnl);
  const yMax = Math.max(...pnl);
  const yPad = (yMax - yMin) * 0.08 || 50;

  // Split into positive / negative traces for green / red fill
  const posY = pnl.map(v => Math.max(v, 0));
  const negY = pnl.map(v => Math.min(v, 0));

  const traces = [
    { x: prices, y: posY, type: "scatter", mode: "lines",
      fill: "tozeroy", fillcolor: "rgba(25,135,84,0.12)",
      line: { color: "transparent" }, hoverinfo: "skip", showlegend: false },
    { x: prices, y: negY, type: "scatter", mode: "lines",
      fill: "tozeroy", fillcolor: "rgba(220,53,69,0.12)",
      line: { color: "transparent" }, hoverinfo: "skip", showlegend: false },
    { x: prices, y: pnl,  type: "scatter", mode: "lines",
      name: "P/L at expiry",
      line: { color: "#0d6efd", width: 2.5 },
      hovertemplate: "<b>$%{x:.2f}</b><br>P/L: $%{y:,.0f}<extra></extra>" },
  ];

  // Shapes: zero line, spot line, breakeven lines
  const shapes = [
    { type: "line",
      x0: prices[0], x1: prices[prices.length - 1], y0: 0, y1: 0,
      line: { color: "#6c757d", width: 1, dash: "dot" } },
    { type: "line",
      x0: state.spot, x1: state.spot, y0: yMin - yPad, y1: yMax + yPad,
      line: { color: "#fd7e14", width: 1.5, dash: "dash" } },
    ...data.breakevens.map(be => ({
      type: "line",
      x0: be, x1: be, y0: yMin - yPad, y1: yMax + yPad,
      line: { color: "#198754", width: 1, dash: "dash" },
    })),
  ];

  // Annotations for spot and breakevens
  const annotations = [
    { x: state.spot, y: yMax + yPad, text: `Spot<br>$${state.spot}`,
      showarrow: false, font: { size: 10, color: "#fd7e14" }, yanchor: "bottom" },
    ...data.breakevens.map(be => ({
      x: be, y: yMin - yPad, text: `BE<br>$${be}`,
      showarrow: false, font: { size: 10, color: "#198754" }, yanchor: "top",
    })),
  ];

  const layout = {
    margin:      { l: 55, r: 15, t: 15, b: 45 },
    xaxis:       { title: "Underlying Price ($)", gridcolor: "#e9ecef" },
    yaxis:       { title: "P/L ($)", tickformat: ",.0f", gridcolor: "#e9ecef", zeroline: false },
    paper_bgcolor: "#fff",
    plot_bgcolor:  "#fafafa",
    shapes,
    annotations,
    legend:      { orientation: "h", y: -0.18 },
    font:        { family: "system-ui, sans-serif", size: 11 },
  };

  Plotly.react("chart", traces, layout, { responsive: true, displayModeBar: false });
}

function renderMetrics(data) {
  const fmt = v => v == null ? '<span class="text-body-secondary">Unlimited</span>'
                             : `$${Math.abs(v).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2})}`;

  const net = data.net_debit_credit;
  const netLabel = net >= 0
    ? `<span class="text-danger">$${net.toFixed(2)} debit</span>`
    : `<span class="text-success">$${Math.abs(net).toFixed(2)} credit</span>`;

  document.getElementById("m-net").innerHTML         = netLabel;
  document.getElementById("m-max-profit").innerHTML  = data.max_profit == null
    ? '<span class="text-body-secondary">Unlimited ∞</span>'
    : `$${data.max_profit.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`;
  document.getElementById("m-max-loss").innerHTML    = data.max_loss == null
    ? '<span class="text-body-secondary">Unlimited ∞</span>'
    : `-$${Math.abs(data.max_loss).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`;
  document.getElementById("m-breakevens").textContent =
    data.breakevens.length ? data.breakevens.map(b => `$${b}`).join(", ") : "None";

  const g = data.greeks;
  document.getElementById("g-delta").textContent = g.delta.toFixed(3);
  document.getElementById("g-gamma").textContent = g.gamma.toFixed(4);
  document.getElementById("g-theta").textContent = g.theta.toFixed(4);
  document.getElementById("g-vega").textContent  = g.vega.toFixed(4);
}


// ─── Utilities ──────────────────────────────────────────────────────────────

function _show(id)       { document.getElementById(id).classList.remove("d-none"); }
function _hide(id)       { document.getElementById(id).classList.add("d-none"); }
function _hideel(el)     { if (el) el.style.display = "none"; }
