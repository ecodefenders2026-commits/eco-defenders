/* ============================================================
   ECO DEFENDERS — LIVE OUTPUT-ONLY DASHBOARD
   Browser never sends sensor values. It only reads the latest
   processed node outputs from the FastAPI server.
============================================================ */

const LIVE_POLL_MS = 2000;
const AppState = {
    selectedNodeId: null,
    nodes: []
};

document.addEventListener("DOMContentLoaded", () => {
    refreshLiveDashboard();
    setInterval(refreshLiveDashboard, LIVE_POLL_MS);
});

async function refreshLiveDashboard() {
    try {
        const response = await fetch("/api/v1/nodes?live_only=true", {
            method: "GET",
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(await getApiError(response));
        }

        const data = await response.json();
        const nodes = Array.isArray(data.nodes) ? data.nodes : [];
        AppState.nodes = nodes;

        updateSystemStatus(nodes);
        renderNodeList(nodes);

        if (!nodes.length) {
            showWaitingState();
            return;
        }

        const selected = chooseNode(nodes);
        renderLiveNode(selected);
        renderRiskDecision(selected);
    } catch (error) {
        showConnectionError(error.message);
    }
}

function chooseNode(nodes) {
    let selected = nodes.find(node => node.node_id === AppState.selectedNodeId);

    if (!selected) {
        selected = [...nodes].sort((a, b) => {
            return String(b.last_received_at || b.timestamp || "")
                .localeCompare(String(a.last_received_at || a.timestamp || ""));
        })[0];
    }

    AppState.selectedNodeId = selected.node_id;
    return selected;
}

function updateSystemStatus(nodes) {
    const dot = document.getElementById("status-dot");
    const label = document.getElementById("system-status-text");

    if (nodes.length) {
        label.textContent = `${nodes.length} LIVE NODE${nodes.length === 1 ? "" : "S"}`;
        dot.classList.remove("status-waiting", "status-error");
        return;
    }

    label.textContent = "WAITING FOR TELEMETRY";
    dot.classList.add("status-waiting");
    dot.classList.remove("status-error");
}

function renderNodeList(nodes) {
    const list = document.getElementById("node-list");
    const count = document.getElementById("nodes-count");
    count.textContent = String(nodes.length);

    if (!nodes.length) {
        list.innerHTML = `<div class="node-empty">No live telemetry received yet.</div>`;
        return;
    }

    list.innerHTML = nodes.map(node => {
        const category = normaliseRisk(node.risk_category, node.risk_score);
        const score = clamp(Number(node.risk_score ?? 0), 0, 100);
        const hazard = node.hazard_type === "FOREST_FIRE" ? "FOREST FIRE" : "FLOOD";
        const active = node.node_id === AppState.selectedNodeId ? " active" : "";
        const warning = Boolean(node.warning_required) || category === "HIGH" || category === "CRITICAL";

        return `
            <div class="node-card${active}">
                <div class="node-card-top">
                    <div>
                        <strong>${escapeHtml(node.node_id || "—")}</strong>
                        <span>${escapeHtml(hazard)}</span>
                    </div>
                    <div class="node-card-score ${riskTextClass(category)}">${Math.round(score)}</div>
                </div>
                <div class="node-card-bottom">
                    <span>${escapeHtml(node.node_name || "Monitoring Node")}</span>
                    <span class="node-card-state ${riskTextClass(category)}">${warning ? "WARNING" : category}</span>
                </div>
            </div>
        `;
    }).join("");
}

function renderLiveNode(node) {
    const hazard = node.hazard_type === "FOREST_FIRE" ? "FOREST FIRE" : "FLOOD";
    const lat = Number(node.latitude);
    const lon = Number(node.longitude);

    document.getElementById("live-node-name").textContent = node.node_name || `Monitoring Node ${node.node_id}`;
    document.getElementById("live-node-id").textContent = node.node_id || "—";
    document.getElementById("live-hazard").textContent = hazard;
    document.getElementById("live-received").textContent = formatReceivedAt(node.last_received_at || node.timestamp);
    document.getElementById("live-status").textContent = node.is_online ? "ONLINE" : "STALE";
    document.getElementById("live-location").textContent = Number.isFinite(lat) && Number.isFinite(lon)
        ? `${lat.toFixed(4)}, ${lon.toFixed(4)}`
        : "—";

    document.getElementById("telemetry-node").textContent = node.node_id || "—";

    if (hazard === "FLOOD") {
        document.getElementById("telemetry-primary").textContent = formatNumber(node.water_level_m, 2, "m");
        document.getElementById("telemetry-secondary").textContent = formatNumber(node.rainfall_mm, 1, "mm");
        document.getElementById("telemetry-flow").textContent = formatNumber(node.river_flow, 1, "m³/s");
        document.getElementById("telemetry-moisture").textContent = formatNumber(node.soil_moisture, 1, "%");
        document.getElementById("telemetry-ambient").textContent = `${formatNumber(node.temperature, 1, "°C")} / ${formatNumber(node.pressure, 0, "hPa")}`;
    } else {
        document.getElementById("telemetry-primary").textContent = formatNumber(node.thermal_temp_c, 1, "°C");
        document.getElementById("telemetry-secondary").textContent = formatNumber(node.pm25_ugm3, 0, "µg/m³");
        document.getElementById("telemetry-flow").textContent = formatNumber(node.wind_speed, 1, "m/s");
        document.getElementById("telemetry-moisture").textContent = formatNumber(node.humidity, 1, "%");
        document.getElementById("telemetry-ambient").textContent = formatNumber(node.temperature, 1, "°C");
    }
}

function renderRiskDecision(node) {
    const hazard = node.hazard_type === "FOREST_FIRE" ? "FOREST_FIRE" : "FLOOD";
    const score = clamp(Number(node.risk_score ?? 0), 0, 100);
    const category = normaliseRisk(node.risk_category, score);
    const warning = Boolean(node.warning_required) || category === "HIGH" || category === "CRITICAL";
    const probability = hazard === "FOREST_FIRE"
        ? Number(node.flood_probability ?? node.fire_probability ?? score / 100)
        : Number(node.flood_probability ?? score / 100);
    const confidence = node.confidence == null ? null : Number(node.confidence);

    document.getElementById("result-node-id").textContent = node.node_id || "—";
    document.getElementById("result-node-hazard").textContent = hazard === "FOREST_FIRE" ? "FOREST FIRE" : "FLOOD";
    document.getElementById("risk-score").textContent = String(Math.round(score));
    document.getElementById("risk-score").style.color = riskColour(category);
    document.getElementById("result-hazard").textContent = hazard === "FOREST_FIRE" ? "FOREST FIRE RISK" : "FLOOD RISK";

    const state = document.getElementById("risk-state");
    state.textContent = category;
    state.className = `state-pill ${riskStateClass(category)}`;

    const warningBox = document.getElementById("warning-box");
    if (warning) {
        warningBox.classList.remove("hidden");
        document.getElementById("warning-title").textContent = `${category} WARNING`;
        document.getElementById("warning-text").textContent = buildWarningText(node, hazard, category);
    } else {
        warningBox.classList.add("hidden");
    }

    if (hazard === "FLOOD") {
        document.getElementById("primary-output").textContent = formatNumber(node.water_level_m, 2, "m");
        document.getElementById("threshold-output").textContent = thresholdText(node.water_level_m, 5.0);
    } else {
        document.getElementById("primary-output").textContent = formatNumber(node.thermal_temp_c, 1, "°C");
        document.getElementById("threshold-output").textContent = thresholdText(node.thermal_temp_c, 65.0);
    }

    document.getElementById("time-output").textContent = formatTime(node.estimated_time_to_threshold);
    document.getElementById("confidence-output").textContent = confidence == null ? "—" : `${Math.round(confidence <= 1 ? confidence * 100 : confidence)}%`;

    const probabilityPct = Number.isFinite(probability) ? Math.round(probability * 100) : score;
    document.getElementById("result-summary").textContent = buildSummary(node, hazard, category, probabilityPct);

    document.getElementById("result-empty").classList.add("hidden");
    document.getElementById("result-content").classList.remove("hidden");
}

function showWaitingState() {
    document.getElementById("result-empty").classList.remove("hidden");
    document.getElementById("result-content").classList.add("hidden");
    document.getElementById("empty-title").textContent = "Waiting for sensor data";
    document.getElementById("empty-text").textContent = "The dashboard will update automatically when a node sends telemetry to the server.";
    document.getElementById("live-node-name").textContent = "Waiting for sensor data";
    document.getElementById("live-node-id").textContent = "—";
}

function showConnectionError(message) {
    const label = document.getElementById("system-status-text");
    const dot = document.getElementById("status-dot");
    label.textContent = "SERVER CONNECTION ERROR";
    dot.classList.add("status-error");
    dot.classList.remove("status-waiting");

    document.getElementById("result-empty").classList.remove("hidden");
    document.getElementById("result-content").classList.add("hidden");
    document.getElementById("empty-title").textContent = "Telemetry unavailable";
    document.getElementById("empty-text").textContent = message || "Unable to reach the live telemetry API.";
}

function buildSummary(node, hazard, category, probabilityPct) {
    if (hazard === "FLOOD") {
        if (category === "HIGH" || category === "CRITICAL") {
            return `The AI identifies a ${category.toLowerCase()} flood risk with an estimated probability of ${probabilityPct}%. River level, rainfall and catchment conditions indicate possible hazard escalation.`;
        }
        return `Current hydrological conditions indicate ${category.toLowerCase()} flood risk. The AI probability estimate is ${probabilityPct}%.`;
    }

    if (category === "HIGH" || category === "CRITICAL") {
        return `The AI identifies a ${category.toLowerCase()} wildfire risk with an estimated probability of ${probabilityPct}%. Thermal and smoke indicators suggest elevated fire activity.`;
    }

    return `Current thermal and atmospheric conditions indicate ${category.toLowerCase()} wildfire risk. The AI probability estimate is ${probabilityPct}%.`;
}

function buildWarningText(node, hazard, category) {
    if (hazard === "FLOOD") {
        const level = Number(node.water_level_m);
        return Number.isFinite(level)
            ? `Node ${node.node_id} reports a river level of ${level.toFixed(2)} m against a 5.0 m danger stage.`
            : `Node ${node.node_id} is reporting elevated flood risk.`;
    }

    const thermal = Number(node.thermal_temp_c);
    const pm25 = Number(node.pm25_ugm3);
    return `Node ${node.node_id} reports thermal hotspot ${Number.isFinite(thermal) ? thermal.toFixed(1) : "—"} °C and PM2.5 ${Number.isFinite(pm25) ? pm25.toFixed(0) : "—"} µg/m³.`;
}

function thresholdText(value, limit) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "—";
    if (numeric >= limit) return "BREACHED";
    return `${Math.max(0, Math.min(999, numeric / limit * 100)).toFixed(0)}% of limit`;
}

function formatReceivedAt(value) {
    if (!value) return "—";
    const raw = String(value);
    const parsed = new Date(raw.includes("T") ? raw : raw.replace(" ", "T") + "Z");
    if (Number.isNaN(parsed.getTime())) return raw;
    return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatNumber(value, decimals, unit) {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(decimals)} ${unit}` : "—";
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, Number(value) || 0));
}

function normaliseRisk(category, score) {
    if (category) {
        const text = String(category).trim().toUpperCase();
        if (text === "VERY LOW" || text === "LOW") return "LOW";
        if (["MODERATE", "HIGH", "CRITICAL"].includes(text)) return text;
    }
    if (score <= 40) return "LOW";
    if (score <= 60) return "MODERATE";
    if (score <= 80) return "HIGH";
    return "CRITICAL";
}

function riskColour(category) {
    switch (category) {
        case "LOW": return "#17865b";
        case "MODERATE": return "#b87800";
        case "HIGH": return "#c15b12";
        case "CRITICAL": return "#c93535";
        default: return "#102033";
    }
}

function riskStateClass(category) {
    return `state-${category.toLowerCase()}`;
}

function riskTextClass(category) {
    return `risk-text-${category.toLowerCase()}`;
}

function formatTime(minutes) {
    if (minutes === null || minutes === undefined || !Number.isFinite(Number(minutes))) return "—";
    const value = Number(minutes);
    if (value <= 0) return "NOW";
    if (value < 60) return `${Math.round(value)} min`;
    return `${Math.floor(value / 60)}h ${Math.round(value % 60)}m`;
}

async function getApiError(response) {
    try {
        const data = await response.json();
        return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    } catch {
        return `Server returned ${response.status}`;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
