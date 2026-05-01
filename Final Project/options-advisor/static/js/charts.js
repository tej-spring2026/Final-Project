/**
 * charts.js — Options Strategy Builder client-side logic
 *
 * Depends on: TICKER, SPOT, EXPIRATIONS (injected by builder.html)
 * Requires:   Plotly (CDN), Tailwind (CDN)
 */

// ─── Application state ──────────────────────────────────────────────────────
const state = {
  ticker:     TICKER,
  spot:       SPOT,
  expiration: null,
  legs: [],       // [{option_type, strike, expiration, quantity, entry_price, label}]
  customMin:  null,
  customMax:  null,
};


// ─── Bootstrap init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("expiration-select");
  sel.addEventListener("change", () => loadChain(sel.value));
  if (sel.options.length > 0) loadChain(sel.value);

  // Load a strategy pre-built in the AI Advisor (if ticker matches)
  const stored = sessionStorage.getItem("advisorStrategy");
  if (stored) {
    try {
      const { ticker: storedTicker, spot: storedSpot, legs: storedLegs } = JSON.parse(stored);
      if (storedTicker === state.ticker && Array.isArray(storedLegs) && storedLegs.length > 0) {
        storedLegs.forEach(leg => {
          state.legs.push({
            ...leg,
            label: `${leg.option_type.toUpperCase()} K=${leg.strike} @ $${Number(leg.entry_price).toFixed(2)} (${leg.expiration})`,
          });
        });
        renderLegsPanel();
        refreshChart();
      }
    } catch (e) { /* ignore malformed data */ }
    sessionStorage.removeItem("advisorStrategy");
  }
});


// ─── Chain loading ──────────────────────────────────────────────────────────

async function loadChain(expiration) {
  state.expiration = expiration;
  _show("chain-loading");
  _hide("chain-container");
  _hide("chain-error");

  let url = `/api/chain?ticker=${encodeURIComponent(state.ticker)}&expiration=${encodeURIComponent(expiration)}`;
  if (state.customMin !== null && state.customMax !== null) {
    url += `&min_strike=${state.customMin}&max_strike=${state.customMax}`;
  }

  try {
    const resp = await fetch(url);
    const data = await resp.json();
    if (data.error) throw new Error(data.error);

    state.spot = data.spot;
    document.getElementById("spot-display").textContent = `$${data.spot.toFixed(2)}`;

    const labelEl = document.getElementById("filter-label");
    if (data.filter && data.filter.label) {
      labelEl.textContent = data.filter.label;
      labelEl.style.display = "";
    } else {
      labelEl.style.display = "none";
    }

    renderChainTable(data.contracts);
    _hide("chain-loading");
    _show("chain-container");

    if (typeof lucide !== "undefined") lucide.createIcons();
  } catch (err) {
    _hide("chain-loading");
    const el = document.getElementById("chain-error");
    el.textContent = `Could not load chain: ${err.message}`;
    _show("chain-error");
  }
}


// ─── Strike range controls ───────────────────────────────────────────────────

function selectFilterMode(mode) {
  const panel      = document.getElementById("custom-range-panel");
  const defaultBtn = document.getElementById("filter-default-btn");
  const customBtn  = document.getElementById("filter-custom-btn");

  if (mode === "custom") {
    panel.style.display = "flex";
    customBtn.classList.add("active");
    defaultBtn.classList.remove("active");
  } else {
    panel.style.display = "none";
    defaultBtn.classList.add("active");
    customBtn.classList.remove("active");
    // If a custom range was active, clear it and reload
    if (state.customMin !== null || state.customMax !== null) {
      state.customMin = null;
      state.customMax = null;
      document.getElementById("min-strike").value = "";
      document.getElementById("max-strike").value = "";
      loadChain(state.expiration);
    }
  }
}

function applyCustomRange() {
  const minVal = parseFloat(document.getElementById("min-strike").value);
  const maxVal = parseFloat(document.getElementById("max-strike").value);

  if (isNaN(minVal) || isNaN(maxVal)) {
    alert("Enter valid numbers for both Min and Max strike.");
    return;
  }
  if (minVal >= maxVal) {
    alert(`Min Strike ($${minVal}) must be less than Max Strike ($${maxVal}).`);
    return;
  }

  state.customMin = minVal;
  state.customMax = maxVal;
  loadChain(state.expiration);
}

function resetRange() {
  state.customMin = null;
  state.customMax = null;
  document.getElementById("min-strike").value = "";
  document.getElementById("max-strike").value = "";
  // Snap segmented control back to Default
  document.getElementById("filter-default-btn").classList.add("active");
  document.getElementById("filter-custom-btn").classList.remove("active");
  document.getElementById("custom-range-panel").style.display = "none";
  loadChain(state.expiration);
}


// ─── Chain table rendering ───────────────────────────────────────────────────

function renderChainTable(contracts) {
  const calls = {}, puts = {};
  contracts.forEach(c => {
    if (c.option_type === "call") calls[c.strike] = c;
    else                          puts[c.strike]  = c;
  });

  const allStrikes = [...new Set(contracts.map(c => c.strike))].sort((a, b) => a - b);

  const atmStrike = allStrikes.reduce((prev, cur) =>
    Math.abs(cur - state.spot) < Math.abs(prev - state.spot) ? cur : prev
  );

  const tbody = document.getElementById("chain-body");
  tbody.innerHTML = "";

  allStrikes.forEach(strike => {
    const call  = calls[strike];
    const put   = puts[strike];
    const isAtm = strike === atmStrike;

    const tr = document.createElement("tr");
    if (isAtm) tr.className = "atm-row";

    tr.innerHTML =
      _callCells(call, strike) +
      `<td class="strike-col text-center">
         ${strike}${isAtm ? '<span class="atm-badge">ATM</span>' : ""}
       </td>` +
      _putCells(put, strike);

    tbody.appendChild(tr);
  });

  // Scroll ATM row into view
  const rows   = tbody.querySelectorAll("tr");
  const atmIdx = allStrikes.indexOf(atmStrike);
  if (rows[atmIdx]) rows[atmIdx].scrollIntoView({ block: "center", behavior: "smooth" });
}

function _callCells(c, strike) {
  if (!c) return '<td colspan="4" class="text-right num text-slate-300" style="border-right:1px solid #e2e8f0">—</td>';
  const iv    = c.iv    != null ? `${c.iv}%`             : "—";
  const delta = c.delta != null ? c.delta.toFixed(2)     : "—";
  const mid   = c.mid   != null && c.mid > 0 ? `$${c.mid.toFixed(2)}` : "—";
  const btns  = c.mid != null && c.mid > 0
    ? `<button class="chain-btn long"  onclick="addLeg('call',${strike},'${c.expiration}',${c.mid},'${c.symbol}',1)">L</button>
       <button class="chain-btn short" style="margin-left:3px" onclick="addLeg('call',${strike},'${c.expiration}',${c.mid},'${c.symbol}',-1)">S</button>`
    : '<span class="text-slate-300 text-xs">—</span>';
  return `<td class="text-right num text-slate-500">${iv}</td>
          <td class="text-right num">${delta}</td>
          <td class="text-right num font-medium">${mid}</td>
          <td class="text-center" style="border-right:1px solid #e2e8f0">${btns}</td>`;
}

function _putCells(c, strike) {
  if (!c) return '<td colspan="4" class="text-left num text-slate-300" style="border-left:1px solid #e2e8f0">—</td>';
  const iv    = c.iv    != null ? `${c.iv}%`             : "—";
  const delta = c.delta != null ? c.delta.toFixed(2)     : "—";
  const mid   = c.mid   != null && c.mid > 0 ? `$${c.mid.toFixed(2)}` : "—";
  const btns  = c.mid != null && c.mid > 0
    ? `<button class="chain-btn long"  onclick="addLeg('put',${strike},'${c.expiration}',${c.mid},'${c.symbol}',1)">L</button>
       <button class="chain-btn short" style="margin-left:3px" onclick="addLeg('put',${strike},'${c.expiration}',${c.mid},'${c.symbol}',-1)">S</button>`
    : '<span class="text-slate-300 text-xs">—</span>';
  return `<td class="text-center" style="border-left:1px solid #e2e8f0">${btns}</td>
          <td class="text-left num font-medium">${mid}</td>
          <td class="text-left num text-slate-500">${iv}</td>
          <td class="text-left num">${delta}</td>`;
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
  const leg  = state.legs[idx];
  const sign = leg.quantity >= 0 ? 1 : -1;
  const newAbs = Math.max(1, Math.abs(leg.quantity) + delta);
  leg.quantity = sign * newAbs;
  renderLegsPanel();
  refreshChart();
}

function setAbsQty(idx, val) {
  const leg  = state.legs[idx];
  const sign = leg.quantity >= 0 ? 1 : -1;
  const abs  = Math.max(1, Math.min(10, parseInt(val) || 1));
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
    emptyEl.classList.remove("hidden");
    listEl.innerHTML = "";
    return;
  }
  emptyEl.classList.add("hidden");

  listEl.innerHTML = state.legs.map((leg, idx) => {
    const isLong    = leg.quantity > 0;
    const absQty    = Math.abs(leg.quantity);
    const sideLabel = isLong ? "LONG" : "SHORT";
    return `
      <div class="leg-item">
        <button class="leg-side-btn ${isLong ? "long" : "short"}"
                onclick="toggleSide(${idx})" title="Toggle Long / Short">
          ${sideLabel}
        </button>
        <span class="leg-label" title="${leg.label}">
          <span style="font-weight:600">${leg.option_type.toUpperCase()}</span>
          <span style="color:#64748b;font-size:0.8rem"> K=${leg.strike}</span>
          <span style="color:#94a3b8;font-size:0.78rem"> @ $${leg.entry_price.toFixed(2)}</span>
        </span>
        <div class="qty-group">
          <button onclick="changeAbsQty(${idx},-1)">−</button>
          <input type="number" value="${absQty}" min="1" max="10"
                 onchange="setAbsQty(${idx}, this.value)">
          <button onclick="changeAbsQty(${idx},1)">+</button>
        </div>
        <button class="leg-remove-btn" onclick="removeLeg(${idx})" title="Remove leg">✕</button>
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

  const posY = pnl.map(v => Math.max(v, 0));
  const negY = pnl.map(v => Math.min(v, 0));

  const traces = [
    { x: prices, y: posY, type: "scatter", mode: "lines",
      fill: "tozeroy", fillcolor: "rgba(5,150,105,0.10)",
      line: { color: "transparent" }, hoverinfo: "skip", showlegend: false },
    { x: prices, y: negY, type: "scatter", mode: "lines",
      fill: "tozeroy", fillcolor: "rgba(220,38,38,0.10)",
      line: { color: "transparent" }, hoverinfo: "skip", showlegend: false },
    { x: prices, y: pnl, type: "scatter", mode: "lines",
      name: "P/L at expiry",
      line: { color: "#2563eb", width: 2.5 },
      hovertemplate: "<b>$%{x:.2f}</b><br>P/L: $%{y:,.0f}<extra></extra>" },
  ];

  const shapes = [
    { type: "line",
      x0: prices[0], x1: prices[prices.length - 1], y0: 0, y1: 0,
      line: { color: "#94a3b8", width: 1, dash: "dot" } },
    { type: "line",
      x0: state.spot, x1: state.spot, y0: yMin - yPad, y1: yMax + yPad,
      line: { color: "#f59e0b", width: 1.5, dash: "dash" } },
    ...data.breakevens.map(be => ({
      type: "line",
      x0: be, x1: be, y0: yMin - yPad, y1: yMax + yPad,
      line: { color: "#059669", width: 1, dash: "dash" },
    })),
  ];

  const annotations = [
    { x: state.spot, y: yMax + yPad, text: `Spot<br>$${state.spot}`,
      showarrow: false, font: { size: 10, color: "#f59e0b" }, yanchor: "bottom" },
    ...data.breakevens.map(be => ({
      x: be, y: yMin - yPad, text: `BE<br>$${be}`,
      showarrow: false, font: { size: 10, color: "#059669" }, yanchor: "top",
    })),
  ];

  Plotly.react("chart", traces, {
    margin:        { l: 52, r: 12, t: 10, b: 42 },
    xaxis:         { title: { text: "Underlying Price at Expiration ($)", font: { size: 11 } }, gridcolor: "#f1f5f9", tickfont: { family: "JetBrains Mono", size: 10 } },
    yaxis:         { title: { text: "Profit / Loss ($)", font: { size: 11 } }, tickformat: ",.0f", gridcolor: "#f1f5f9", zeroline: false, tickfont: { family: "JetBrains Mono", size: 10 } },
    paper_bgcolor: "#fff",
    plot_bgcolor:  "#fff",
    shapes,
    annotations,
    legend:        { orientation: "h", y: -0.22 },
    font:          { family: "Inter, system-ui, sans-serif", size: 11 },
  }, { responsive: true, displayModeBar: false });
}

function renderMetrics(data) {
  const net = data.net_debit_credit;
  document.getElementById("m-net").innerHTML = net >= 0
    ? `<span style="color:#dc2626">$${net.toFixed(2)} debit</span>`
    : `<span style="color:#059669">$${Math.abs(net).toFixed(2)} credit</span>`;

  document.getElementById("m-max-profit").innerHTML = data.max_profit == null
    ? '<span style="color:#94a3b8">Unlimited ∞</span>'
    : `$${data.max_profit.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  document.getElementById("m-max-loss").innerHTML = data.max_loss == null
    ? '<span style="color:#94a3b8">Unlimited ∞</span>'
    : `-$${Math.abs(data.max_loss).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  document.getElementById("m-breakevens").textContent =
    data.breakevens.length ? data.breakevens.map(b => `$${b}`).join(", ") : "None";

  const g = data.greeks;
  document.getElementById("g-delta").textContent = g.delta.toFixed(3);
  document.getElementById("g-gamma").textContent = g.gamma.toFixed(4);
  document.getElementById("g-theta").textContent = g.theta.toFixed(4);
  document.getElementById("g-vega").textContent  = g.vega.toFixed(4);
}


// ─── Utilities ──────────────────────────────────────────────────────────────

function _show(id)   { document.getElementById(id).classList.remove("hidden"); }
function _hide(id)   { document.getElementById(id).classList.add("hidden"); }
function _hideel(el) { if (el) el.style.display = "none"; }
