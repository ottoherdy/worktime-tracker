/**
 * Worktime Tracker Lovelace Card
 * Vanilla Web Component — no build step, no external dependencies.
 * Auto-registered via async_register_extra_module_url in __init__.py
 */

const ENTITY_TODAY = "sensor.today_hours_today";
const ENTITY_WEEK = "sensor.this_week_hours_this_week";
const ENTITY_SWITCH = "switch.today_auto_departure";
const DOMAIN = "worktime_tracker";

const STATUS_COLOR = {
  at_work: "var(--success-color, #4caf50)",
  overtime: "var(--warning-color, #ff9800)",
  done: "var(--info-color, #2196f3)",
  off_duty: "var(--disabled-color, #9e9e9e)",
};

const STATUS_LABEL = {
  at_work: "At work",
  overtime: "Overtime",
  done: "Done",
  off_duty: "Off duty",
};

function _fmt(val) {
  return val !== undefined && val !== null && val !== "—" && val !== "" ? val : "—";
}

function _sign(num) {
  if (num === undefined || num === null) return "—";
  const n = parseFloat(num);
  if (isNaN(n)) return "—";
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "h";
}

function _hoursHuman(hours) {
  if (hours === undefined || hours === null) return "—";
  const h = parseFloat(hours);
  if (isNaN(h) || h === 0) return "—";
  const totalMin = Math.round(h * 60);
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  return `${hh}h ${String(mm).padStart(2, "0")}m`;
}

function _progressPct(hours, target) {
  if (!target || !hours) return 0;
  return Math.min(100, Math.round((parseFloat(hours) / parseFloat(target)) * 100));
}

class WorktimeTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._intervalId = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._intervalId = setInterval(() => this._render(), 30000);
  }

  disconnectedCallback() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  setConfig(config) {
    // No required config — card is self-contained
    this._config = config || {};
  }

  getCardSize() {
    return 5;
  }

  _callService(service, data = {}) {
    if (!this._hass) return;
    this._hass.callService(DOMAIN, service, data);
  }

  _toggleSwitch() {
    if (!this._hass) return;
    const swState = this._hass.states[ENTITY_SWITCH];
    if (!swState) return;
    const domain = "switch";
    const svc = swState.state === "on" ? "turn_off" : "turn_on";
    this._hass.callService(domain, svc, { entity_id: ENTITY_SWITCH });
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;

    const todayState = hass.states[ENTITY_TODAY];
    const weekState = hass.states[ENTITY_WEEK];
    const switchState = hass.states[ENTITY_SWITCH];

    if (!todayState) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--primary-text-color)">
            Integration not found — check that Worktime Tracker is installed.
          </div>
        </ha-card>`;
      return;
    }

    const attr = todayState.attributes || {};
    const weekAttr = weekState ? weekState.attributes || {} : {};
    const swOn = switchState ? switchState.state === "on" : false;

    const status = attr.status || "off_duty";
    const statusColor = STATUS_COLOR[status] || STATUS_COLOR.off_duty;
    const statusLabel = STATUS_LABEL[status] || status;

    const arrival = _fmt(attr.arrival);
    const plannedEnd = _fmt(attr.planned_end);
    const departure = _fmt(attr.departure);
    const lunch = attr.lunch || "";
    const hours = parseFloat(attr.hours) || 0;
    const overtime = parseFloat(attr.overtime) || 0;
    const timeRemaining = _fmt(attr.time_remaining);
    const dailyTarget = parseFloat(attr.daily_net_target) || 8.0;
    const pct = _progressPct(hours, dailyTarget);

    const weekHours = weekState ? parseFloat(weekState.state) || 0 : 0;
    const weekTarget = parseFloat(weekAttr.weekly_target) || 40;
    const weekOvertime = parseFloat(weekAttr.overtime) || 0;

    const lunchBadge = lunch === "yes"
      ? `<span class="badge lunch-yes">🍽 Lunch: yes</span>`
      : lunch === "no"
      ? `<span class="badge lunch-no">🍽 Lunch: no</span>`
      : `<span class="badge lunch-unknown">🍽 Lunch: ?</span>`;

    // Recent days table (last 7)
    const recent = (attr.recent_days || []).slice(0, 7);
    const recentRows = recent.map((d) => {
      const isSick = d.type === "sick";
      const missingPunch = d.punch_out_missing;
      const typeIcon = isSick ? " 🤒" : missingPunch ? " ⚠" : "";
      return `
        <tr>
          <td>${d.date || "—"}</td>
          <td>${d.weekday || "—"}</td>
          <td style="text-align:right">${isSick ? "sick" : (d.human_readable || "—")}${typeIcon}</td>
        </tr>`;
    }).join("");

    // Departure display — show actual departure if done, else planned end
    const depDisplay = status === "done" ? departure : plannedEnd;

    const html = `
      <style>
        :host {
          --wt-radius: 12px;
          --wt-gap: 12px;
        }
        ha-card {
          padding: 16px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .title {
          font-size: 1.1em;
          font-weight: 600;
          color: var(--primary-text-color);
        }
        .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 20px;
          font-size: 0.82em;
          font-weight: 500;
        }
        .status-badge {
          background: ${statusColor};
          color: #fff;
        }
        .lunch-yes { background: var(--success-color, #4caf50); color: #fff; }
        .lunch-no  { background: var(--error-color, #f44336); color: #fff; }
        .lunch-unknown { background: var(--disabled-color, #9e9e9e); color: #fff; }

        .time-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          margin-bottom: 10px;
        }
        .time-item {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .time-label {
          font-size: 0.72em;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .time-value {
          font-size: 1.3em;
          font-weight: 700;
          color: var(--primary-text-color);
        }
        .hours-big {
          font-size: 2em;
          font-weight: 800;
          color: ${statusColor};
          margin: 4px 0;
        }
        .progress-wrap {
          background: var(--divider-color, #e0e0e0);
          border-radius: 6px;
          height: 8px;
          overflow: hidden;
          margin: 8px 0 12px;
        }
        .progress-fill {
          height: 100%;
          background: ${statusColor};
          width: ${pct}%;
          transition: width 0.4s ease;
          border-radius: 6px;
        }
        .buttons {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin: 10px 0;
        }
        button {
          flex: 1 1 calc(50% - 8px);
          padding: 8px 4px;
          border: none;
          border-radius: var(--wt-radius);
          background: var(--primary-color, #03a9f4);
          color: #fff;
          font-size: 0.85em;
          font-weight: 600;
          cursor: pointer;
          min-width: 80px;
        }
        button:active { opacity: 0.8; }
        button.secondary {
          background: var(--secondary-background-color, #f5f5f5);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color, #e0e0e0);
        }
        button.danger {
          background: var(--error-color, #f44336);
        }
        button.on {
          background: var(--success-color, #4caf50);
        }
        .divider {
          height: 1px;
          background: var(--divider-color, #e0e0e0);
          margin: 12px 0;
        }
        .week-row {
          display: flex;
          justify-content: space-between;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        .week-row span b {
          color: var(--primary-text-color);
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.82em;
          margin-top: 6px;
        }
        thead th {
          color: var(--secondary-text-color);
          text-align: left;
          font-weight: 500;
          padding: 2px 4px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        tbody td {
          padding: 3px 4px;
          color: var(--primary-text-color);
        }
        tbody tr:nth-child(even) td {
          background: var(--secondary-background-color, rgba(0,0,0,0.03));
        }
        .remaining-label {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
      </style>

      <ha-card>
        <div class="header">
          <span class="title">Worktime Tracker</span>
          <span class="badge status-badge">${statusLabel}</span>
        </div>

        <div class="time-row">
          <div class="time-item">
            <span class="time-label">Arrival</span>
            <span class="time-value">${arrival}</span>
          </div>
          <div class="time-item">
            <span class="time-label">${status === "done" ? "Departed" : "Planned end"}</span>
            <span class="time-value">${depDisplay}</span>
          </div>
          <div class="time-item">
            <span class="time-label">Hours worked</span>
            <span class="hours-big">${_hoursHuman(hours)}</span>
          </div>
        </div>

        <div class="progress-wrap">
          <div class="progress-fill"></div>
        </div>

        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          ${lunchBadge}
          <span class="remaining-label">
            ${status === "off_duty"
              ? "Not at work"
              : status === "done"
              ? `Overtime: ${_sign(overtime)}`
              : `Remaining: ${timeRemaining}`}
          </span>
        </div>

        <div class="buttons">
          <button id="btn-arrival" onclick="">✅ Log Arrival</button>
          <button id="btn-departure" class="secondary" onclick="">🚪 Log Departure</button>
          <button id="btn-lunch-yes" class="secondary" onclick="">🍽 Lunch ✓</button>
          <button id="btn-lunch-no" class="danger" onclick="">🚫 No Lunch</button>
        </div>

        <div style="display:flex;gap:8px;margin-bottom:8px">
          <button id="btn-switch" class="${swOn ? "on" : "secondary"}" style="flex:1">
            ${swOn ? "🔔 Auto-depart: ON" : "🔕 Auto-depart: OFF"}
          </button>
          <button id="btn-reset" class="danger" style="flex:0 0 auto;min-width:60px">Reset</button>
        </div>

        <div class="divider"></div>

        <div class="week-row">
          <span>This week: <b>${weekHours.toFixed(2)}h</b></span>
          <span>Overtime: <b>${_sign(weekOvertime)}</b></span>
          <span>Target: <b>${weekTarget}h</b></span>
        </div>

        <div class="divider"></div>

        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Day</th>
              <th style="text-align:right">Hours</th>
            </tr>
          </thead>
          <tbody>
            ${recentRows || '<tr><td colspan="3" style="text-align:center;color:var(--secondary-text-color)">No history yet</td></tr>'}
          </tbody>
        </table>
      </ha-card>`;

    this.shadowRoot.innerHTML = html;

    // Attach event listeners after render
    this.shadowRoot.getElementById("btn-arrival")?.addEventListener("click", () => {
      this._callService("log_arrival");
    });
    this.shadowRoot.getElementById("btn-departure")?.addEventListener("click", () => {
      this._callService("log_departure");
    });
    this.shadowRoot.getElementById("btn-lunch-yes")?.addEventListener("click", () => {
      this._callService("set_lunch", { had_lunch: true });
    });
    this.shadowRoot.getElementById("btn-lunch-no")?.addEventListener("click", () => {
      this._callService("set_lunch", { had_lunch: false });
    });
    this.shadowRoot.getElementById("btn-switch")?.addEventListener("click", () => {
      this._toggleSwitch();
    });
    this.shadowRoot.getElementById("btn-reset")?.addEventListener("click", () => {
      if (confirm("Reset today's tracking?")) {
        this._callService("reset_today");
      }
    });
  }
}

customElements.define("worktime-tracker-card", WorktimeTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worktime-tracker-card",
  name: "Worktime Tracker",
  description: "Daily work time tracker with arrival, departure, lunch and weekly overview.",
  preview: false,
  documentationURL: "https://github.com/ottoherdy/worktime-tracker",
});
