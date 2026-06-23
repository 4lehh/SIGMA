// ── Configuración WebSocket ──────────────────────────────────────────────────
const WS_URL = `ws://${location.hostname}:8765`;
const MAX_HISTORY = 30;
const MAX_LOGS    = 50;

// ── Estado ───────────────────────────────────────────────────────────────────
const history = {};   // { sensorId: [{ temp, humidity, vpd, ts }] }
let ws;

// ── Variables del Gráfico Global ──────────────────────────────────────────────
let vpdChartInstance = null;
const palette = ['#2aff7a', '#5b9fff', '#ffb830', '#a3d977', '#ff4f4f'];

// ── Helpers ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const safeId = str => str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

function vpdColor(vpd) {
  if (vpd < 0.4)  return '#5b9fff';
  if (vpd <= 0.8) return '#2aff7a';
  if (vpd <= 1.2) return '#ffb830';
  return '#ff4f4f';
}

function vpdStatus(vpd, roomType) {
  const ranges = { 0: [0.8, 1.0], 1: [1.0, 1.2], 2: [1.0, 1.2] };
  const [lo, hi] = ranges[roomType] ?? [0.8, 1.2];
  if (vpd < lo)  return { text: '▼ VPD bajo',   color: '#5b9fff' };
  if (vpd > hi)  return { text: '▲ VPD alto',   color: '#ff4f4f' };
  return { text: '● Rango óptimo', color: '#2aff7a' };
}

function sparklinePath(values, w, h) {
  if (values.length < 2) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 0.01;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return `M${pts.join('L')}`;
}

// ── Render sensor card ────────────────────────────────────────────────────────
function renderCard(s) {
  const id  = s.identificador;
  const hist = history[id] || [];
  const vpd  = s.VPD;
  const act  = s.actuators || { cooling: 0, heating: 0, humidifier: 0, light: 0 };

  const vpdPct   = Math.min((vpd / 2) * 100, 100).toFixed(1);
  const vpdCol   = vpdColor(vpd);
  const vpdSt    = vpdStatus(vpd, s.room_type);
  const tempHist = hist.map(h => h.temp);
  const spW = 260, spH = 40;
  const path = sparklinePath(tempHist, spW, spH);

  const actItems = [
    { key: 'cooling',    icon: '❄️', label: 'Cooling'  },
    { key: 'heating',    icon: '🔥', label: 'Heating'  },
    { key: 'humidifier', icon: '💧', label: 'Humid.'   },
    { key: 'light',      icon: '☀️', label: 'Luz'      },
  ];

  const actHTML = actItems.map(a => {
    const val = act[a.key] ?? 0;
    const active = val > 0 ? 'active' : '';
    return `<div class="actuator ${active}">
      <div class="actuator-icon">${a.icon}</div>
      <div class="actuator-name">${a.label}</div>
      <div class="actuator-val">${val.toFixed(2)}</div>
    </div>`;
  }).join('');

  const sid = safeId(id);
  
  // NUEVO: Verificamos si hay anomalía para agregar la clase css inicial
  const anomalyClass = s.is_anomaly ? 'anomaly-alert' : '';

  return `
  <div class="sensor-card ${anomalyClass}" id="card-${sid}">
    <div class="card-header">
      <div class="card-title">${id}</div>
      <div class="room-badge room-${s.room_type}">${s.room_label}</div>
    </div>
    <div class="card-body">
      <div class="metrics">
        <div class="metric">
          <div class="metric-label">Temp. Sala</div>
          <div class="metric-value" id="val-temp-${sid}">
            ${s.room_temp.toFixed(2)}<span class="metric-unit">°C</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-label">Humedad</div>
          <div class="metric-value" id="val-hum-${sid}">
            ${(s.humidity * 100).toFixed(1)}<span class="metric-unit">%</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-label">Temp. Hoja</div>
          <div class="metric-value" id="val-leaf-${sid}">
            ${s.leaf_temp.toFixed(2)}<span class="metric-unit">°C</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-label">VPD</div>
          <div class="metric-value" id="val-vpd-${sid}" style="color:${vpdCol}">
            ${vpd.toFixed(4)}<span class="metric-unit">kPa</span>
          </div>
        </div>
        <div class="metric full">
          <div class="metric-label">VPD — Déficit de presión de vapor</div>
          <div class="vpd-bar-wrap">
            <div class="vpd-bar-track">
              <div class="vpd-bar-fill" id="vpd-bar-${sid}"
                   style="width:${vpdPct}%; background:${vpdCol}"></div>
            </div>
            <div class="vpd-labels"><span>0.0</span><span>0.8</span><span>1.2</span><span>2.0+</span></div>
            <div class="vpd-status" id="vpd-st-${sid}" style="color:${vpdSt.color}">${vpdSt.text}</div>
          </div>
        </div>
      </div>

      ${path ? `
      <div>
        <div class="actuators-label">Temperatura — Historial</div>
        <svg class="sparkline" viewBox="0 0 ${spW} ${spH}" preserveAspectRatio="none">
          <path d="${path}" fill="none" stroke="${vpdCol}" stroke-width="1.5" opacity=".8"/>
        </svg>
      </div>` : ''}

      <div class="actuators-section">
        <div class="actuators-label">Actuadores</div>
        <div class="actuators" id="act-${sid}">${actHTML}</div>
      </div>
    </div>
    <div class="card-footer">
      <span>Última actualización: <span id="ts-${sid}">${s.timestamp}</span></span>
      <span><span id="hist-len-${sid}">${hist.length}</span> muestras</span>
    </div>
  </div>`;
}

// ── Actualizar card existente ─────────────────────────────────────────────────
function updateCard(s) {
  const id  = s.identificador;
  const sid = safeId(id);
  const vpd = s.VPD;
  const act = s.actuators || { cooling: 0, heating: 0, humidifier: 0, light: 0 };

  const vpdCol = vpdColor(vpd);
  const vpdSt  = vpdStatus(vpd, s.room_type);
  const vpdPct = Math.min((vpd / 2) * 100, 100).toFixed(1);

  const set = (elId, val) => { const el = document.getElementById(elId); if (el) el.innerHTML = val; };

  set(`val-temp-${sid}`, `${s.room_temp.toFixed(2)}<span class="metric-unit">°C</span>`);
  set(`val-hum-${sid}`,  `${(s.humidity * 100).toFixed(1)}<span class="metric-unit">%</span>`);
  set(`val-leaf-${sid}`, `${s.leaf_temp.toFixed(2)}<span class="metric-unit">°C</span>`);

  const vpdEl = document.getElementById(`val-vpd-${sid}`);
  if (vpdEl) {
    vpdEl.style.color = vpdCol;
    vpdEl.innerHTML = `${vpd.toFixed(4)}<span class="metric-unit">kPa</span>`;
  }

  const bar = document.getElementById(`vpd-bar-${sid}`);
  if (bar) { bar.style.width = `${vpdPct}%`; bar.style.background = vpdCol; }

  const st = document.getElementById(`vpd-st-${sid}`);
  if (st) { st.style.color = vpdSt.color; st.textContent = vpdSt.text; }

  set(`ts-${sid}`, s.timestamp);
  set(`hist-len-${sid}`, (history[id] || []).length);

  const actDiv = document.getElementById(`act-${sid}`);
  if (actDiv) {
    const items = [
      { key: 'cooling', icon: '❄️', label: 'Cooling' },
      { key: 'heating', icon: '🔥', label: 'Heating' },
      { key: 'humidifier', icon: '💧', label: 'Humid.' },
      { key: 'light', icon: '☀️', label: 'Luz' },
    ];
    actDiv.innerHTML = items.map(a => {
      const val = act[a.key] ?? 0;
      return `<div class="actuator ${val > 0 ? 'active' : ''}">
        <div class="actuator-icon">${a.icon}</div>
        <div class="actuator-name">${a.label}</div>
        <div class="actuator-val">${val.toFixed(2)}</div>
      </div>`;
    }).join('');
  }

  const hist = (history[id] || []).map(h => h.temp);
  const spW = 260, spH = 40;
  const path = sparklinePath(hist, spW, spH);
  const svg = document.querySelector(`#card-${sid} .sparkline`);
  if (svg && path) svg.innerHTML = `<path d="${path}" fill="none" stroke="${vpdCol}" stroke-width="1.5" opacity=".8"/>`;

  const card = document.getElementById(`card-${sid}`);
  if (card) {
    // NUEVO: Verificamos si debemos activar o desactivar la alerta
    if (s.is_anomaly) {
      card.classList.add('anomaly-alert');
      card.classList.remove('updated');
    } else {
      card.classList.remove('anomaly-alert');
      card.classList.add('updated');
      setTimeout(() => card.classList.remove('updated'), 800);
    }
  }
}

// ── Inicializar Gráfico Chart.js ─────────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById('vpdChart').getContext('2d');
  vpdChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: []
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 }, // Desactiva animación para evitar "saltos" en tiempo real
      scales: {
        x: {
          grid: { color: '#1e3024', drawBorder: false },
          ticks: { color: '#4a6650', font: { family: "'IBM Plex Mono', monospace", size: 10 } }
        },
        y: {
          grid: { color: '#1e3024', drawBorder: false },
          ticks: { color: '#4a6650', font: { family: "'IBM Plex Mono', monospace", size: 10 } },
          min: 0,
          suggestedMax: 2.0
        }
      },
      plugins: {
        legend: {
          labels: { color: '#c8e0cc', font: { family: "'IBM Plex Mono', monospace", size: 11 }, usePointStyle: true, boxWidth: 6 }
        },
        tooltip: {
          backgroundColor: '#111a14', titleColor: '#4a6650', bodyColor: '#c8e0cc', borderColor: '#1e3024', borderWidth: 1
        }
      }
    }
  });
}

// ── Actualizar Gráfico ───────────────────────────────────────────────────────
function updateChartData(s) {
  if (!vpdChartInstance) return;

  const ts = s.timestamp;
  
  // Agregar timestamp si no existe en el eje X
  if (!vpdChartInstance.data.labels.includes(ts)) {
    vpdChartInstance.data.labels.push(ts);
    if (vpdChartInstance.data.labels.length > MAX_HISTORY) {
      vpdChartInstance.data.labels.shift();
      vpdChartInstance.data.datasets.forEach(d => d.data.shift());
    }
  }

  // Buscar o crear la línea (dataset) para este sensor
  let dataset = vpdChartInstance.data.datasets.find(d => d.label === s.identificador);
  if (!dataset) {
    const color = palette[vpdChartInstance.data.datasets.length % palette.length];
    dataset = {
      label: s.identificador,
      data: new Array(vpdChartInstance.data.labels.length - 1).fill(null), // rellenar histórico faltante
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 1,
      tension: 0.3 // Suaviza la línea
    };
    vpdChartInstance.data.datasets.push(dataset);
  }

  // Emparejar el dato con el índice de tiempo actual
  const labelIdx = vpdChartInstance.data.labels.indexOf(ts);
  dataset.data[labelIdx] = s.VPD;

  vpdChartInstance.update();
}

// ── Procesar mensaje ──────────────────────────────────────────────────────────
function processSensor(s) {
  const id = s.identificador;
  if (!history[id]) history[id] = [];
  history[id].push({ temp: s.room_temp, hum: s.humidity, vpd: s.VPD, ts: s.timestamp });
  if (history[id].length > MAX_HISTORY) history[id].shift();

  const chartContainer = $('chart-container');
  const grid = $('sensors-grid');
  const noData = $('no-data');
  const logPanel = $('log-panel');

  if (document.getElementById(`card-${safeId(id)}`)) {
    updateCard(s);
  } else {
    grid.style.display = 'grid';
    noData.style.display = 'none';
    logPanel.style.display = 'block';
    grid.insertAdjacentHTML('beforeend', renderCard(s));
  }

  if (chartContainer.style.display === 'none') {
    chartContainer.style.display = 'block';
    initChart();
  }

  // Actualizar el gráfico principal
  updateChartData(s);

  // NUEVO: Lógica de Log separada para darle énfasis a las anomalías
  if (s.is_anomaly) {
    addLog(`ANOMALÍA: ${s.identificador} reporta parámetros críticos!!! VPD=${s.VPD.toFixed(4)}`, true);
  } else {
    addLog(`${s.identificador} — T:${s.room_temp.toFixed(2)}°C  H:${(s.humidity*100).toFixed(1)}%  VPD:${s.VPD.toFixed(4)}`, false);
  }
}

function addLog(msg, isAlert = false) {
  const el = $('log-entries');
  const now = new Date().toTimeString().slice(0, 8);
  const alertStyle = isAlert ? 'style="color: var(--red); font-weight: 600;"' : '';
  
  el.insertAdjacentHTML('afterbegin',
    `<div class="log-entry"><span class="ts">${now}</span><span class="msg" ${alertStyle}>${msg}</span></div>`);
  while (el.children.length > MAX_LOGS) el.removeChild(el.lastChild);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    $('conn-dot').className   = 'dot live';
    $('conn-label').textContent = 'En vivo';
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === 'snapshot') {
      Object.values(msg.data).forEach(processSensor);
    } else if (msg.type === 'update') {
      processSensor(msg.sensor);
    }
  };

  ws.onclose = () => {
    $('conn-dot').className   = 'dot error';
    $('conn-label').textContent = 'Sin conexión — reintentando…';
    setTimeout(connect, 3000);
  };

  ws.onerror = () => ws.close();
}

// Iniciar conexión
connect();
