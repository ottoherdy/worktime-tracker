/**
 * Worktime Tracker Lovelace Card — v2.5.0
 * Vanilla Web Component, no build step. Auto-loaded via add_extra_js_url.
 *
 * Config (all optional, defaults shown):
 *   show_topbar: false       // centered date
 *   show_today: true         // Today card with elapsed time and actions
 *   show_this_week: true     // This week list with totals
 *   show_last_week: true     // Last week list
 *   show_this_month: false   // This month summary
 *   show_last_month: false   // Last month summary
 *   show_history: true       // History compact list
 *   show_lookup: true        // Date-picker box at the bottom
 *   show_footer: true        // "Saved locally" + Export/Sheets links
 *   show_edit: true          // edit pencil + row-tap → modal
 *   history_limit: 10        // rows in history
 *   padding: 14              // outer padding in px
 *   max_width: 420           // max card width (0 = fluid / fill container)
 *   theme: "auto"            // "auto" (follow sun.sun) | "light" | "dark"
 *   entity_prefix: ""        // for multi-instance, e.g. "home"
 *
 * Styling: every visual token is a CSS variable on :host. Override via
 * card_mod or a theme. See README.md for the full list.
 */

const DOMAIN = "worktime_tracker";

function _entities(prefix) {
  const p = prefix ? `${prefix}_` : "";
  return {
    today: `sensor.${p}today_hours_today`,
    week: `sensor.${p}this_week_hours_this_week`,
    last_week: `sensor.${p}last_week_hours_last_week`,
    this_month: `sensor.${p}this_month_hours_this_month`,
    last_month: `sensor.${p}last_month_hours_last_month`,
    sw: `switch.${p}today_auto_departure`,
  };
}

const DEFAULTS = {
  show_topbar: false,
  show_today: true,
  show_this_week: true,
  show_last_week: true,
  show_this_month: false,
  show_last_month: false,
  show_history: true,
  show_lookup: true,
  show_footer: true,
  show_edit: true,
  history_limit: 10,
  padding: 14,
  max_width: 420,
  theme: "auto",
  entity_prefix: "",
};

const SECTIONS = [
  ["show_topbar", "Topbar (date)"],
  ["show_today", "Today card"],
  ["show_this_week", "This week list"],
  ["show_last_week", "Last week list"],
  ["show_this_month", "This month summary"],
  ["show_last_month", "Last month summary"],
  ["show_history", "History list"],
  ["show_lookup", "Look up day (date picker)"],
  ["show_footer", "Footer (Export / Sheets)"],
  ["show_edit", "Inline edit (pencil + row-tap)"],
];

const ICON = {
  briefcase: `<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
  reset: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>`,
  arrowRight: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 7l5 5-5 5"/></svg>`,
  arrowLeft: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H6M11 7l-5 5 5 5"/></svg>`,
  lunch: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M7 2v8a3 3 0 1 0 6 0V2"/><path d="M10 14v8"/><path d="M17 2c2 4 2 8 0 12v8"/></svg>`,
  clock: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>`,
  search: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>`,
  pencil: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M14.7 4.3l4.9 4.9L8.6 20.3 3.7 21l.7-4.9z"/></svg>`,
};

function _todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function _formatTopbarDate() {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short", month: "short", day: "numeric",
  }).format(new Date()).replace(",", " ·");
}

function _hoursToHM(hours) {
  if (hours == null || isNaN(parseFloat(hours))) return { h: 0, m: 0 };
  const total = Math.max(0, Math.round(parseFloat(hours) * 60));
  return { h: Math.floor(total / 60), m: total % 60 };
}

function _fmtHM(hours) {
  const { h, m } = _hoursToHM(hours);
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

function _fmtDeltaHours(diff) {
  if (diff == null || isNaN(parseFloat(diff))) return "0.00h";
  const d = parseFloat(diff);
  const sign = d >= 0 ? "+" : "−";
  return `${sign}${Math.abs(d).toFixed(2)}h`;
}

function _isoToMMDD(iso) {
  if (!iso) return "";
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  return `${parts[1]}-${parts[2]}`;
}

function _miniBarPct(hours, target = 8) {
  const h = parseFloat(hours) || 0;
  if (h <= 0) return 0;
  const max = target * 1.5;
  return Math.min(100, Math.round((h / max) * 100));
}

function _timeForInput(val) {
  if (!val || val === "—") return "";
  return val;
}

function _lunchLabel(status) {
  if (status === "yes") return "yes";
  if (status === "no") return "no";
  return "—";
}

function _weekdayShort(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "T12:00:00");
  return new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(d);
}

class WorktimeTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._tick = null;
    this._editing = null;
    this._stateSig = "";
    this._lookupDate = _todayIso();
  }

  set hass(hass) {
    this._hass = hass;
    // While the edit modal is open, leave the DOM alone so the open
    // time picker, focused input, and partially-typed values survive
    // both the tick and incoming hass updates.
    if (this._editing && this.shadowRoot.getElementById("modal-backdrop")) return;
    const sig = this._computeSig();
    if (sig !== this._stateSig) {
      this._stateSig = sig;
      this._render();
    } else {
      this._renderLive();
    }
  }

  connectedCallback() {
    // Tick only nudges the elapsed-time / progress bar via targeted DOM
    // mutations; the rest of the shadow DOM stays put so anything you
    // interact with (buttons, scroll position, hovers) isn't wiped.
    this._tick = setInterval(() => this._renderLive(), 1000);
  }

  disconnectedCallback() {
    if (this._tick) { clearInterval(this._tick); this._tick = null; }
  }

  setConfig(config) {
    this._config = config || {};
    this._stateSig = "";
  }

  getCardSize() { return 8; }

  _cfg(key) {
    if (this._config && key in this._config) return this._config[key];
    return DEFAULTS[key];
  }

  _entityIds() {
    return _entities(this._cfg("entity_prefix") || "");
  }

  _callService(service, data = {}) {
    if (!this._hass) return;
    const prefix = this._cfg("entity_prefix") || "";
    const payload = { ...data };
    if (prefix) payload.entry_prefix = prefix;
    this._hass.callService(DOMAIN, service, payload);
  }

  _toggleSwitch() {
    if (!this._hass) return;
    const ids = this._entityIds();
    const swState = this._hass.states[ids.sw];
    if (!swState) return;
    const svc = swState.state === "on" ? "turn_off" : "turn_on";
    this._hass.callService("switch", svc, { entity_id: ids.sw });
  }

  _openEdit(day) {
    if (!day) return;
    this._editing = {
      date: day.date,
      arrival: _timeForInput(day.arrival),
      departure: _timeForInput(day.departure),
      lunch: day.lunch && day.lunch !== "—" ? day.lunch : "",
      type: day.type === "none" ? "normal" : (day.type || "normal"),
      hours: day.hours != null ? String(day.hours) : "",
    };
    this._render();
  }

  _closeEdit() {
    this._editing = null;
    this._render();
  }

  _saveEdit() {
    if (!this._editing) return;
    const e = this._editing;
    const payload = { date: e.date, type: e.type };
    if (e.type === "normal") {
      if (e.arrival) payload.arrival = e.arrival;
      if (e.departure) payload.departure = e.departure;
      if (e.lunch) payload.lunch = e.lunch;
    }
    // hours override applies to any type (lets you do half-day sick etc.)
    if (e.hours !== "") payload.hours = parseFloat(e.hours);
    this._callService("edit_day", payload);
    this._closeEdit();
  }

  _useDarkTheme() {
    const t = this._cfg("theme");
    if (t === "dark") return true;
    if (t === "light") return false;
    const sun = this._hass?.states?.["sun.sun"];
    return sun?.state === "below_horizon";
  }

  _computeSig() {
    const hass = this._hass;
    if (!hass) return "";
    const ids = this._entityIds();
    const t = hass.states[ids.today]?.attributes || {};
    const w = hass.states[ids.week];
    const lw = hass.states[ids.last_week];
    const m = hass.states[ids.this_month];
    const lm = hass.states[ids.last_month];
    const sw = hass.states[ids.sw];
    const sun = hass.states["sun.sun"]?.state;
    return [
      t.status, t.arrival, t.departure, t.lunch,
      t.daily_net_target, t.auto_departure_time, t.auto_lunch_default,
      (t.recent_days || []).length,
      w?.state, (w?.attributes?.days || []).length, w?.attributes?.overtime,
      lw?.state, (lw?.attributes?.days || []).length, lw?.attributes?.overtime,
      m?.state, m?.attributes?.month, m?.attributes?.overtime,
      lm?.state, lm?.attributes?.month, lm?.attributes?.overtime,
      sw?.state,
      sun,
      this._lookupDate,
    ].join("|");
  }

  _renderLive() {
    if (this._editing && this.shadowRoot.getElementById("modal-backdrop")) return;
    if (!this._hass) return;
    if (!this.shadowRoot.querySelector(".elapsed")) {
      // No DOM yet — let _render build it.
      this._render();
      return;
    }
    const ids = this._entityIds();
    const t = this._hass.states[ids.today];
    if (!t) return;
    const attr = t.attributes || {};
    const hours = parseFloat(attr.hours) || 0;
    const target = parseFloat(attr.daily_net_target) || 8;
    const { h, m } = _hoursToHM(hours);
    const overTarget = hours > target;

    const elapsedEl = this.shadowRoot.querySelector(".elapsed");
    if (elapsedEl) {
      const key = `${h}|${m}`;
      if (elapsedEl.dataset.k !== key) {
        elapsedEl.dataset.k = key;
        elapsedEl.innerHTML =
          `<span>${h}</span><span class="unit">h</span>` +
          `<span>${String(m).padStart(2, "0")}</span><span class="unit">m</span>`;
      }
    }

    const fillEl = this.shadowRoot.querySelector(".fill");
    if (fillEl) {
      const pct = Math.min(100, (hours / target) * 100);
      fillEl.style.width = `${pct}%`;
      fillEl.classList.toggle("over", overTarget);
    }

    const subEl = this.shadowRoot.querySelector(".elapsed-sub");
    if (subEl) {
      const sk = `${target}|${hours.toFixed(3)}`;
      if (subEl.dataset.sk !== sk) {
        subEl.dataset.sk = sk;
        let html = `<span>Target <span class="mono">${_fmtHM(target)}</span></span>`;
        if (hours > 0) {
          const cls = overTarget ? "over" : "under";
          const txt = overTarget
            ? `+${_fmtHM(hours - target)} over`
            : `−${_fmtHM(target - hours)} to go`;
          html += `<span class="dot"></span><span class="delta ${cls}">${txt}</span>`;
        }
        subEl.innerHTML = html;
      }
    }
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;
    if (this._editing && this.shadowRoot.getElementById("modal-backdrop")) return;

    const ids = this._entityIds();
    const todayState = hass.states[ids.today];
    const weekState = hass.states[ids.week];
    const lastWeekState = hass.states[ids.last_week];
    const monthState = hass.states[ids.this_month];
    const lastMonthState = hass.states[ids.last_month];
    const switchState = hass.states[ids.sw];

    if (!todayState) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--primary-text-color)">
            Worktime Tracker entities not found
            ${this._cfg("entity_prefix") ? `for prefix "${this._cfg("entity_prefix")}"` : ""}.
            Check Settings → Devices & Services → Worktime Tracker.
          </div>
        </ha-card>`;
      return;
    }

    const attr = todayState.attributes || {};
    const weekAttr = weekState ? weekState.attributes || {} : {};
    const lastWeekAttr = lastWeekState ? lastWeekState.attributes || {} : {};
    const monthAttr = monthState ? monthState.attributes || {} : {};
    const lastMonthAttr = lastMonthState ? lastMonthState.attributes || {} : {};

    const status = attr.status || "off_duty";
    const onClock = status === "at_work" || status === "overtime";
    const done = status === "done";

    const hours = parseFloat(attr.hours) || 0;
    const target = parseFloat(attr.daily_net_target) || 8.0;
    const overTarget = hours > target;
    const overAmount = hours - target;
    const { h: elapsedH, m: elapsedM } = _hoursToHM(hours);
    const progressPct = Math.min(100, (hours / target) * 100);

    const arrival = attr.arrival || "—";
    const departure = attr.departure || (onClock ? (attr.planned_end || "—") : "—");
    const lunchStatus = attr.lunch || "unknown";
    const lunchOn = lunchStatus === "yes" || (lunchStatus === "unknown" && !!attr.auto_lunch_default);

    const autoOn = switchState && switchState.state === "on";
    const autoOutTimeRaw = attr.auto_departure_time || "15:00";
    const autoOutTime = autoOutTimeRaw.slice(0, 5);

    const weekHours = weekState ? parseFloat(weekState.state) || 0 : 0;
    const weekDays = weekAttr.days || [];
    const weekFilled = weekDays.filter((d) => d && d.type !== "none" && parseFloat(d.hours) > 0);
    const weekAvgH = weekFilled.length ? weekHours / weekFilled.length : 0;

    const lastWeekHours = lastWeekState ? parseFloat(lastWeekState.state) || 0 : 0;
    const lastWeekDays = lastWeekAttr.days || [];
    const lastWeekFilled = lastWeekDays.filter((d) => d && d.type !== "none" && parseFloat(d.hours) > 0);
    const lastWeekAvgH = lastWeekFilled.length ? lastWeekHours / lastWeekFilled.length : 0;

    const monthHours = monthState ? parseFloat(monthState.state) || 0 : 0;
    const monthOvertime = parseFloat(monthAttr.overtime) || 0;
    const monthLabel = monthAttr.month || "This month";

    const lastMonthHours = lastMonthState ? parseFloat(lastMonthState.state) || 0 : 0;
    const lastMonthOvertime = parseFloat(lastMonthAttr.overtime) || 0;
    const lastMonthLabel = lastMonthAttr.month || "Last month";

    const historyLimit = parseInt(this._cfg("history_limit"), 10) || 10;
    const recentAll = attr.recent_days || [];
    const history = recentAll.slice(0, historyLimit);

    const showTopbar = !!this._cfg("show_topbar");
    const showToday = !!this._cfg("show_today");
    const showThisWeek = !!this._cfg("show_this_week");
    const showLastWeek = !!this._cfg("show_last_week");
    const showThisMonth = !!this._cfg("show_this_month");
    const showLastMonth = !!this._cfg("show_last_month");
    const showHistory = !!this._cfg("show_history");
    const showLookup = !!this._cfg("show_lookup");
    const showFooter = !!this._cfg("show_footer");

    const padding = parseInt(this._cfg("padding"), 10) || 14;
    const maxWidthRaw = parseInt(this._cfg("max_width"), 10);
    const maxWidthCss = !isNaN(maxWidthRaw) && maxWidthRaw > 0 ? `${maxWidthRaw}px` : "none";
    const useDark = this._useDarkTheme();

    // Pool of every known day, for the look-up box. Today is added
    // synthetically so the picker can show "in progress" days.
    const lookupPool = [];
    const todayIso = _todayIso();
    if (recentAll.length) lookupPool.push(...recentAll);
    for (const wd of weekDays) if (wd?.date) lookupPool.push(wd);
    for (const wd of lastWeekDays) if (wd?.date) lookupPool.push(wd);
    if (attr.status && (attr.arrival || hours > 0)) {
      lookupPool.push({
        date: todayIso,
        weekday: _weekdayShort(todayIso),
        arrival: attr.arrival || "—",
        departure: attr.departure || "—",
        lunch: lunchStatus,
        type: "normal",
        hours: hours,
      });
    }

    this._dayTables = {
      this_week: weekDays,
      last_week: lastWeekDays,
      history: history,
      lookup: lookupPool,
    };

    const elapsedHtml = `
      <span>${elapsedH}</span><span class="unit">h</span>
      <span>${String(elapsedM).padStart(2, "0")}</span><span class="unit">m</span>`;

    const pillHtml = onClock
      ? `<span class="pill on-clock"><span class="pulse"></span> On the clock</span>`
      : done
      ? `<span class="pill done">Done</span>`
      : `<span class="pill off">Off duty</span>`;

    const subOverHtml = hours > 0
      ? (overTarget
          ? `<span class="dot"></span><span class="delta over">+${_fmtHM(overAmount)} over</span>`
          : `<span class="dot"></span><span class="delta under">−${_fmtHM(target - hours)} to go</span>`)
      : "";

    const weekListHtml = this._renderWeekList(weekDays, target);
    const lastWeekListHtml = this._renderWeekList(lastWeekDays, target);
    const historyListHtml = this._renderHistoryList(history, target);
    const lookupBoxHtml = this._renderLookupBox(lookupPool, target);

    const modalHtml = this._editing ? this._renderModal(this._editing) : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles(padding, maxWidthCss)}</style>
      <ha-card class="${useDark ? "theme-dark" : ""}">
        <div class="app">
          ${showTopbar ? `
            <header class="topbar">
              <span class="mono date">${_formatTopbarDate()}</span>
            </header>` : ""}

          ${showToday ? `
            <section class="today">
              <div class="today-head">
                <div class="left">
                  <span class="badge-icon">${ICON.briefcase}</span>
                  Today
                </div>
                <div class="right">${pillHtml}</div>
              </div>

              <div class="elapsed mono" data-k="${elapsedH}|${elapsedM}">${elapsedHtml}</div>
              <div class="elapsed-sub" data-sk="${target}|${hours.toFixed(3)}">
                <span>Target <span class="mono">${_fmtHM(target)}</span></span>
                ${subOverHtml}
              </div>

              <div class="track">
                <div class="fill ${overTarget ? "over" : ""}" style="width:${progressPct}%"></div>
                <div class="mark" style="left:100%"></div>
              </div>

              <div class="io">
                <div>
                  <div class="io-label">Arrival</div>
                  <div class="io-value mono ${arrival === "—" ? "dim" : ""}">${arrival}</div>
                </div>
                <div>
                  <div class="io-label">${done ? "Departed" : "Departure"}</div>
                  <div class="io-value mono ${departure === "—" ? "dim" : ""}">${departure}</div>
                </div>
                <div>
                  <div class="io-label">Lunch</div>
                  <div class="io-value mono ${lunchStatus === "yes" || lunchStatus === "no" ? "" : "dim"}">${_lunchLabel(lunchStatus)}</div>
                </div>
              </div>

              <div class="actions actions-3">
                <button class="btn" id="btn-arrival">${ICON.arrowRight}Arrival</button>
                <button class="btn" id="btn-reset" title="Reset today">${ICON.reset}Reset</button>
                <button class="btn" id="btn-departure">${ICON.arrowLeft}Departure</button>
              </div>
              <div class="actions-grid">
                <button class="btn toggle" id="btn-lunch" aria-pressed="${lunchOn}">
                  ${ICON.lunch}Lunch<span class="meta">${lunchOn ? "yes" : "no"}</span>
                </button>
                <button class="btn toggle" id="btn-auto" aria-pressed="${autoOn}">
                  ${ICON.clock}Auto-out<span class="meta">${autoOutTime}</span>
                </button>
              </div>
            </section>` : ""}

          ${showThisWeek ? `
            <section class="section">
              <div class="section-head"><div class="section-title">This week</div></div>
              <div class="list">
                ${weekListHtml}
                <div class="totals">
                  <span>${weekFilled.length} ${weekFilled.length === 1 ? "day" : "days"} · avg <b class="mono">${_fmtHM(weekAvgH)}</b></span>
                </div>
              </div>
            </section>` : ""}

          ${showLastWeek ? `
            <section class="section">
              <div class="section-head"><div class="section-title">Last week</div></div>
              <div class="list">
                ${lastWeekListHtml}
                <div class="totals">
                  <span>${lastWeekFilled.length} ${lastWeekFilled.length === 1 ? "day" : "days"} · avg <b class="mono">${_fmtHM(lastWeekAvgH)}</b></span>
                </div>
              </div>
            </section>` : ""}

          ${showThisMonth ? this._renderMonthBlock("This month", monthLabel, monthHours, monthOvertime) : ""}
          ${showLastMonth ? this._renderMonthBlock("Last month", lastMonthLabel, lastMonthHours, lastMonthOvertime) : ""}

          ${showHistory ? `
            <section class="section">
              <div class="section-head"><div class="section-title">History</div></div>
              <div class="list">${historyListHtml}</div>
            </section>` : ""}

          ${showLookup ? `
            <section class="section">
              <div class="section-head">
                <div class="section-title">Look up day</div>
              </div>
              ${lookupBoxHtml}
            </section>` : ""}

          ${showFooter ? `
            <footer class="foot">
              <span>Saved locally</span>
              <span class="foot-links">
                <a href="#" id="link-export">Export</a>
                <a href="#" id="link-sheets">Sheets</a>
              </span>
            </footer>` : ""}
        </div>
      </ha-card>
      ${modalHtml}`;

    this._wireEvents();
  }

  _renderMonthBlock(label, monthName, hours, overtime) {
    return `
      <section class="section">
        <div class="section-head">
          <div class="section-title">${label}<span class="title-meta mono">${monthName}</span></div>
        </div>
        <div class="month-card">
          <div class="month-row">
            <span class="month-k">Hours</span>
            <span class="month-v mono">${hours.toFixed(2)}h</span>
          </div>
          <div class="month-row">
            <span class="month-k">Overtime</span>
            <span class="month-v mono ${overtime >= 0 ? "pos" : "neg"}">${_fmtDeltaHours(overtime)}</span>
          </div>
        </div>
      </section>`;
  }

  _renderWeekList(days, target) {
    if (!days || days.length === 0) return `<div class="row empty"><div class="day">—</div><div class="times">No data</div><div class="hours">—</div><div></div></div>`;
    const todayIso = _todayIso();
    const editable = !!this._cfg("show_edit");
    return days.map((d, i) => {
      const empty = d.type === "none" || (d.arrival === "—" && d.hours === 0);
      const isToday = d.date === todayIso;
      const hoursNum = parseFloat(d.hours) || 0;
      const overClass = hoursNum > target ? "over" : "under";
      const rowClasses = ["row"];
      if (empty) rowClasses.push("empty");
      if (isToday) rowClasses.push("today");
      const timesHtml = empty
        ? `—`
        : `${d.arrival || "—"}<span class="sep">→</span>${d.departure || "—"}`;
      const hoursHtml = empty
        ? "—"
        : d.type === "sick" ? "sick"
        : d.type === "off" ? "off"
        : d.type === "flex" ? "flex"
        : _fmtHM(hoursNum);
      const editCell = editable
        ? `<div class="edit" data-row="${i}" title="Edit">${ICON.pencil}</div>`
        : `<div></div>`;
      return `
        <div class="${rowClasses.join(" ")}" data-row="${i}">
          <div class="day">${d.weekday || "—"}<span class="date">${_isoToMMDD(d.date)}</span></div>
          <div class="times">${timesHtml}</div>
          <div class="hours ${overClass}">${hoursHtml}</div>
          ${editCell}
        </div>`;
    }).join("");
  }

  _renderHistoryList(days, target) {
    if (!days || days.length === 0) return `<div class="history-row"><div class="date">—</div><div class="day">—</div><div class="mini"></div><div class="hours">—</div></div>`;
    const editable = !!this._cfg("show_edit");
    return days.map((d, i) => {
      const hoursNum = parseFloat(d.hours) || 0;
      const pct = _miniBarPct(hoursNum, target);
      const overTarget = hoursNum > target;
      const editClass = editable ? "editable" : "";
      const hoursLabel = d.type === "sick" ? "sick"
        : d.type === "off" ? "off"
        : d.type === "flex" ? "flex"
        : _fmtHM(hoursNum);
      return `
        <div class="history-row ${editClass}" data-row="${i}">
          <div class="date">${d.date || "—"}</div>
          <div class="day">${d.weekday || "—"}</div>
          <div class="mini"><span class="${overTarget ? "over" : ""}" style="width:${pct}%"></span></div>
          <div class="hours">${hoursLabel}</div>
        </div>`;
    }).join("");
  }

  _renderLookupBox(pool, target) {
    const date = this._lookupDate || _todayIso();
    const match = (pool || []).find((d) => d.date === date);
    const editable = !!this._cfg("show_edit");
    const editBtn = (match && editable)
      ? `<button class="btn ghost" id="lookup-edit">${ICON.pencil} Edit</button>`
      : "";

    let body;
    if (!match) {
      body = `
        <div class="lookup-row empty">
          <span class="lookup-k">No data</span>
          <span class="lookup-v dim mono">—</span>
        </div>`;
    } else {
      const hoursNum = parseFloat(match.hours) || 0;
      const overTarget = hoursNum > target;
      const typeLabel = match.type === "sick" ? "Sick"
        : match.type === "off" ? "Off"
        : match.type === "flex" ? "Flex"
        : "Normal";
      const arrival = match.arrival || "—";
      const departure = match.departure || "—";
      const lunch = _lunchLabel(match.lunch);
      const hoursTxt = match.type === "sick" || match.type === "off" || match.type === "flex"
        ? `${hoursNum.toFixed(2)}h`
        : _fmtHM(hoursNum);
      body = `
        <div class="lookup-row">
          <span class="lookup-k">Type</span>
          <span class="lookup-v">${typeLabel}</span>
        </div>
        <div class="lookup-row">
          <span class="lookup-k">Arrival</span>
          <span class="lookup-v mono ${arrival === "—" ? "dim" : ""}">${arrival}</span>
        </div>
        <div class="lookup-row">
          <span class="lookup-k">Departure</span>
          <span class="lookup-v mono ${departure === "—" ? "dim" : ""}">${departure}</span>
        </div>
        <div class="lookup-row">
          <span class="lookup-k">Lunch</span>
          <span class="lookup-v mono ${lunch === "—" ? "dim" : ""}">${lunch}</span>
        </div>
        <div class="lookup-row total">
          <span class="lookup-k">Hours</span>
          <span class="lookup-v mono ${overTarget ? "over" : ""}">${hoursTxt}</span>
        </div>`;
    }

    return `
      <div class="lookup-card">
        <div class="lookup-controls">
          <input type="date" id="lookup-date" value="${date}" max="${_todayIso()}">
          ${editBtn}
        </div>
        ${body}
      </div>`;
  }

  _renderModal(e) {
    const isLeave = e.type !== "normal";
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal">
          <h3>Edit ${e.date}</h3>

          <div class="field">
            <label>Type</label>
            <select id="ed-type">
              <option value="normal" ${e.type === "normal" ? "selected" : ""}>Normal</option>
              <option value="sick" ${e.type === "sick" ? "selected" : ""}>Sick</option>
              <option value="flex" ${e.type === "flex" ? "selected" : ""}>Flex</option>
              <option value="off" ${e.type === "off" ? "selected" : ""}>Off / vacation</option>
            </select>
          </div>

          <div class="field" id="ed-field-arrival" style="${isLeave ? "display:none" : ""}">
            <label>Arrival</label>
            <input type="time" id="ed-arrival" value="${e.arrival}">
          </div>

          <div class="field" id="ed-field-departure" style="${isLeave ? "display:none" : ""}">
            <label>Departure</label>
            <input type="time" id="ed-departure" value="${e.departure}">
          </div>

          <div class="field" id="ed-field-lunch" style="${isLeave ? "display:none" : ""}">
            <label>Lunch</label>
            <select id="ed-lunch">
              <option value="" ${!e.lunch ? "selected" : ""}>— (keep current)</option>
              <option value="yes" ${e.lunch === "yes" ? "selected" : ""}>Yes</option>
              <option value="no" ${e.lunch === "no" ? "selected" : ""}>No</option>
            </select>
          </div>

          <div class="field">
            <label>Hours override (blank = default)</label>
            <input type="number" id="ed-hours" min="0" max="24" step="0.5" value="${e.hours}">
            <div class="field-hint">For half-day sick or partial flex, set the credited hours here.</div>
          </div>

          <div class="row-actions">
            <button class="btn" id="ed-cancel">Cancel</button>
            <button class="btn primary" id="ed-save">Save</button>
          </div>
        </div>
      </div>`;
  }

  _wireEvents() {
    const $ = (id) => this.shadowRoot.getElementById(id);

    $("btn-arrival")?.addEventListener("click", () => this._callService("log_arrival"));
    $("btn-departure")?.addEventListener("click", () => this._callService("log_departure"));
    $("btn-reset")?.addEventListener("click", () => {
      if (confirm("Reset today's tracking?")) this._callService("reset_today");
    });
    $("btn-lunch")?.addEventListener("click", (ev) => {
      const on = ev.currentTarget.getAttribute("aria-pressed") === "true";
      this._callService("set_lunch", { had_lunch: !on });
    });
    $("btn-auto")?.addEventListener("click", () => this._toggleSwitch());
    $("link-export")?.addEventListener("click", (ev) => { ev.preventDefault(); this._callService("export_today"); });
    $("link-sheets")?.addEventListener("click", (ev) => { ev.preventDefault(); this._callService("export_today"); });

    $("lookup-date")?.addEventListener("change", (ev) => {
      this._lookupDate = ev.target.value || _todayIso();
      this._stateSig = "";
      this._render();
    });
    $("lookup-edit")?.addEventListener("click", () => {
      const pool = this._dayTables?.lookup || [];
      const match = pool.find((d) => d.date === this._lookupDate);
      if (match) this._openEdit(match);
    });

    const editable = !!this._cfg("show_edit");
    if (editable) {
      const tableMap = [
        ["show_this_week", "this_week"],
        ["show_last_week", "last_week"],
        ["show_this_month", null],
        ["show_last_month", null],
        ["show_history", "history"],
      ];
      const sections = this.shadowRoot.querySelectorAll("section.section");
      let idx = 0;
      for (const [cfgKey, dataKey] of tableMap) {
        if (!this._cfg(cfgKey)) continue;
        const sec = sections[idx++];
        if (!sec || !dataKey) continue;
        sec.querySelectorAll(".row, .history-row").forEach((row) => {
          row.style.cursor = "pointer";
          row.addEventListener("click", () => {
            const i = parseInt(row.getAttribute("data-row"), 10);
            const day = (this._dayTables[dataKey] || [])[i];
            this._openEdit(day);
          });
        });
      }
    }

    if (this._editing) {
      $("ed-cancel")?.addEventListener("click", () => this._closeEdit());
      $("modal-backdrop")?.addEventListener("click", (ev) => {
        if (ev.target.id === "modal-backdrop") this._closeEdit();
      });
      $("ed-save")?.addEventListener("click", () => {
        const e = this._editing;
        e.type = $("ed-type").value;
        e.arrival = $("ed-arrival")?.value || "";
        e.departure = $("ed-departure")?.value || "";
        e.lunch = $("ed-lunch")?.value || "";
        e.hours = $("ed-hours")?.value || "";
        this._saveEdit();
      });
      $("ed-type")?.addEventListener("change", (ev) => {
        const isLeave = ev.target.value !== "normal";
        $("ed-field-arrival").style.display = isLeave ? "none" : "";
        $("ed-field-departure").style.display = isLeave ? "none" : "";
        $("ed-field-lunch").style.display = isLeave ? "none" : "";
      });
    }
  }

  _styles(padding, maxWidthCss) {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');

      :host {
        --wt-pad: ${padding}px;
        --wt-maxw: ${maxWidthCss};

        --wt-bg:       #f4f3ee;
        --wt-paper:    #fbfaf6;
        --wt-card:     #ffffff;
        --wt-ink:      #15151a;
        --wt-ink-2:    #3a3a44;
        --wt-muted:    #8a8a94;
        --wt-muted-2:  #b6b6be;
        --wt-line:     #e7e5dd;
        --wt-line-2:   #efede6;
        --wt-accent:       #4338ca;
        --wt-accent-soft:  #ecebff;
        --wt-good:         #1f8a5b;
        --wt-warn:         #b45309;
        --wt-danger:       #b91c1c;
        display: block;
      }
      ha-card.theme-dark {
        --wt-bg:       #14141a;
        --wt-paper:    #1c1c24;
        --wt-card:     #20202a;
        --wt-ink:      #f3f2ed;
        --wt-ink-2:    #c8c8d0;
        --wt-muted:    #8f8f99;
        --wt-muted-2:  #5d5d68;
        --wt-line:     #2e2e38;
        --wt-line-2:   #26262f;
        --wt-accent:       #a39bff;
        --wt-accent-soft:  #2a2856;
        --wt-good:         #4ade80;
        --wt-warn:         #f59e0b;
        --wt-danger:       #f87171;
      }

      ha-card {
        background: var(--wt-bg);
        border: none;
        border-radius: 0;
        padding: 0;
        box-shadow: none;
        color: var(--wt-ink);
        font-family: 'Geist', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        font-size: 14px;
        letter-spacing: -0.005em;
        -webkit-font-smoothing: antialiased;
      }
      .app {
        max-width: var(--wt-maxw, 420px);
        margin: 0 auto;
        padding: var(--wt-pad, 14px) var(--wt-pad, 14px) calc(var(--wt-pad, 14px) * 2);
      }
      .mono { font-family: 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace; font-feature-settings: 'tnum', 'zero'; }

      .topbar { display: flex; align-items: center; justify-content: center; padding: 4px 6px 12px; }
      .topbar .date { font-size: 12px; color: var(--wt-muted); }

      /* TODAY */
      .today {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 16px;
        padding: 12px 12px 10px;
      }
      .today-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 6px;
      }
      .today-head .left {
        display: flex; align-items: center; gap: 8px;
        font-size: 14px; font-weight: 500; color: var(--wt-ink);
      }
      .badge-icon {
        width: 26px; height: 26px;
        border-radius: 8px;
        background: var(--wt-ink);
        color: var(--wt-card);
        display: inline-flex; align-items: center; justify-content: center;
      }
      .badge-icon svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
      .today-head .right { display: flex; align-items: center; gap: 8px; }

      .pill {
        display: inline-flex; align-items: center; gap: 8px;
        height: 26px; padding: 0 12px; border-radius: 999px;
        font-size: 13px; font-weight: 500;
      }
      .pill.on-clock { background: var(--wt-accent-soft); color: var(--wt-accent); }
      .pill.done { background: var(--wt-paper); color: var(--wt-ink-2); border: 1px solid var(--wt-line); }
      .pill.off { background: var(--wt-paper); color: var(--wt-muted); border: 1px solid var(--wt-line); }
      .pulse {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--wt-accent);
        box-shadow: 0 0 0 0 rgba(67,56,202,.5);
        animation: wt-pulse 1.8s infinite;
      }
      @keyframes wt-pulse {
        0% { box-shadow: 0 0 0 0 rgba(67,56,202,.5); }
        70% { box-shadow: 0 0 0 7px rgba(67,56,202,0); }
        100% { box-shadow: 0 0 0 0 rgba(67,56,202,0); }
      }

      .elapsed {
        display: flex; align-items: baseline; gap: 4px;
        font-weight: 500; font-size: 56px; line-height: 1;
        letter-spacing: -0.035em;
        padding: 2px 2px 4px;
      }
      .elapsed .unit {
        font-family: 'Geist', sans-serif;
        font-size: 14px; color: var(--wt-muted);
        margin-left: 4px; margin-right: 6px;
        font-weight: 400; letter-spacing: 0;
      }
      .elapsed-sub {
        font-size: 13px; color: var(--wt-muted);
        display: flex; gap: 10px; align-items: center;
        padding: 0 2px;
      }
      .elapsed-sub .delta.over { color: var(--wt-warn); font-weight: 500; }
      .elapsed-sub .delta.under { color: var(--wt-muted); font-weight: 500; }
      .elapsed-sub .dot { width: 3px; height: 3px; border-radius: 50%; background: var(--wt-muted-2); }

      .track {
        margin: 8px 0 10px;
        height: 6px; border-radius: 999px;
        background: var(--wt-line-2);
        position: relative;
        overflow: visible;
      }
      .fill {
        height: 100%; border-radius: 999px;
        background: var(--wt-ink);
        transition: width .5s cubic-bezier(.2,.7,.2,1);
      }
      .fill.over { background: var(--wt-warn); }
      .mark { position: absolute; top: -3px; bottom: -3px; width: 1px; background: rgba(0,0,0,.18); }
      .theme-dark .mark { background: rgba(255,255,255,.18); }

      .io {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        border: 1px solid var(--wt-line);
        border-radius: 12px;
        overflow: hidden;
        background: var(--wt-paper);
      }
      .io > div { padding: 8px 10px; border-right: 1px solid var(--wt-line-2); }
      .io > div:last-child { border-right: none; }
      .io-label {
        font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--wt-muted); font-weight: 500;
        margin-bottom: 2px;
      }
      .io-value {
        font-weight: 500; font-size: 18px;
        letter-spacing: -0.01em;
      }
      .io-value.dim { color: var(--wt-muted); }

      .actions { margin-top: 8px; display: grid; gap: 6px; }
      .actions-3 { grid-template-columns: 1fr 1fr 1fr; }
      .actions-grid { margin-top: 6px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
      .btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 7px;
        height: 42px; padding: 0 12px;
        border-radius: 11px;
        border: 1px solid var(--wt-line);
        background: var(--wt-card);
        font-family: inherit; font-size: 14px; font-weight: 500;
        color: var(--wt-ink); cursor: pointer;
        transition: transform .08s ease, background .12s ease, border-color .12s ease;
        letter-spacing: -0.005em;
      }
      .btn:active { transform: translateY(1px); }
      .btn.primary { background: var(--wt-ink); color: var(--wt-card); border-color: var(--wt-ink); }
      .btn.ghost { background: transparent; }
      .btn .icon { width: 16px; height: 16px; flex-shrink: 0; }
      .btn .meta { color: var(--wt-muted); font-size: 12px; margin-left: 2px; }
      .btn.toggle[aria-pressed="true"] .meta {
        color: var(--wt-ink); font-weight: 600;
      }
      .btn.toggle[aria-pressed="true"] .meta::before {
        content: ""; display: inline-block;
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--wt-accent);
        margin-right: 5px; vertical-align: middle;
      }

      /* Sections */
      .section { margin-top: 16px; }
      .section-head { padding: 0 2px; margin-bottom: 6px; }
      .section-title {
        font-size: 14px; font-weight: 500;
        letter-spacing: -0.01em;
        color: var(--wt-ink);
      }
      .section-title .title-meta {
        color: var(--wt-muted); font-weight: 500; font-size: 12px;
        margin-left: 8px;
      }

      .list {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 12px;
        overflow: hidden;
      }
      .row {
        display: grid;
        grid-template-columns: 46px 1fr auto 24px;
        align-items: center;
        padding: 9px 14px;
        border-bottom: 1px solid var(--wt-line-2);
        gap: 10px;
        font-size: 14px;
      }
      .row:last-child { border-bottom: none; }
      .row .day { font-weight: 500; font-size: 14px; }
      .row .day .date {
        display: block; font-size: 10px; color: var(--wt-muted); margin-top: 1px;
        font-family: 'Geist Mono', monospace; letter-spacing: 0;
      }
      .row .times {
        font-family: 'Geist Mono', monospace; font-size: 14px;
        color: var(--wt-ink-2);
        letter-spacing: -0.005em;
      }
      .row .times .sep { color: var(--wt-muted-2); margin: 0 4px; }
      .row .hours {
        font-family: 'Geist Mono', monospace; font-weight: 500; font-size: 15px;
        text-align: right;
      }
      .row .hours.over { color: var(--wt-warn); }
      .row .hours.under { color: var(--wt-ink); }
      .row .edit {
        color: var(--wt-muted-2);
        display: inline-flex; align-items: center; justify-content: center;
        cursor: pointer;
        height: 24px; width: 24px;
        border-radius: 6px;
      }
      .row .edit:hover { color: var(--wt-ink); background: var(--wt-line-2); }
      .row.today { background: var(--wt-accent-soft); }
      .row.today .day { color: var(--wt-accent); }
      .row.empty .times,
      .row.empty .hours { color: var(--wt-muted-2); }

      .totals {
        display: flex; align-items: center;
        padding: 9px 14px;
        background: var(--wt-paper);
        border-top: 1px solid var(--wt-line);
        font-size: 13px;
        color: var(--wt-muted);
      }
      .totals b { color: var(--wt-ink); font-weight: 500; font-family: 'Geist Mono', monospace; }

      /* Month summary */
      .month-card {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 12px;
        padding: 8px 14px;
      }
      .month-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 0;
      }
      .month-row + .month-row { border-top: 1px solid var(--wt-line-2); }
      .month-k { font-size: 13px; color: var(--wt-muted); }
      .month-v { font-size: 16px; font-weight: 500; }
      .month-v.pos { color: var(--wt-good); }
      .month-v.neg { color: var(--wt-warn); }

      /* History compact */
      .history-row {
        display: grid;
        grid-template-columns: 86px 36px 1fr auto;
        padding: 8px 14px;
        align-items: center;
        border-bottom: 1px solid var(--wt-line-2);
        gap: 10px;
        font-size: 14px;
      }
      .history-row:last-child { border-bottom: none; }
      .history-row.editable { cursor: pointer; }
      .history-row .date { font-family: 'Geist Mono', monospace; font-size: 13px; color: var(--wt-ink-2); }
      .history-row .day { font-size: 12px; color: var(--wt-muted); }
      .history-row .mini { height: 3px; background: var(--wt-line-2); border-radius: 999px; overflow: hidden; }
      .history-row .mini > span { display: block; height: 100%; background: var(--wt-ink); border-radius: 999px; }
      .history-row .mini > span.over { background: var(--wt-warn); }
      .history-row .hours { font-family: 'Geist Mono', monospace; font-weight: 500; font-size: 14px; text-align: right; }

      /* Look-up box */
      .lookup-card {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 12px;
        padding: 10px 14px 12px;
      }
      .lookup-controls {
        display: flex; align-items: center; gap: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--wt-line-2);
        margin-bottom: 6px;
      }
      .lookup-controls input[type="date"] {
        flex: 1;
        padding: 7px 10px;
        border: 1px solid var(--wt-line);
        border-radius: 10px;
        background: var(--wt-paper);
        color: var(--wt-ink);
        font-family: 'Geist Mono', monospace;
        font-size: 14px;
        color-scheme: light;
      }
      .theme-dark .lookup-controls input[type="date"] { color-scheme: dark; }
      .lookup-controls .btn { height: 34px; padding: 0 10px; gap: 4px; font-size: 13px; }
      .lookup-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 0;
        font-size: 14px;
      }
      .lookup-row + .lookup-row { border-top: 1px solid var(--wt-line-2); }
      .lookup-row.total { padding-top: 7px; margin-top: 2px; }
      .lookup-row.total .lookup-v { font-size: 16px; font-weight: 600; }
      .lookup-row.empty { padding: 12px 0 4px; }
      .lookup-k { color: var(--wt-muted); font-size: 12px; }
      .lookup-v { color: var(--wt-ink); font-weight: 500; }
      .lookup-v.dim { color: var(--wt-muted-2); }
      .lookup-v.over { color: var(--wt-warn); }

      .foot {
        margin-top: 18px;
        display: flex; justify-content: space-between; align-items: center;
        color: var(--wt-muted); font-size: 11px;
        padding: 0 4px;
      }
      .foot a { color: var(--wt-muted); text-decoration: none; cursor: pointer; }
      .foot a:hover { color: var(--wt-ink); }
      .foot-links { display: flex; gap: 14px; }

      @media (max-width: 360px) { .elapsed { font-size: 48px; } .io-value { font-size: 16px; } }

      /* Modal */
      .modal-backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.55);
        display: flex; align-items: center; justify-content: center;
        z-index: 999;
      }
      .modal {
        background: var(--wt-card); color: var(--wt-ink);
        border-radius: 16px; padding: 18px;
        width: min(420px, 92vw); max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      }
      .modal h3 { margin: 0 0 12px; font-size: 1.05em; font-weight: 600; }
      .modal .field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
      .modal .field label {
        font-size: 10px; color: var(--wt-muted);
        text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500;
      }
      .modal .field-hint { font-size: 11px; color: var(--wt-muted); margin-top: 2px; }
      .modal input, .modal select {
        padding: 10px; font-size: 14px; font-family: inherit;
        border: 1px solid var(--wt-line); border-radius: 10px;
        background: var(--wt-card); color: var(--wt-ink);
        color-scheme: light;
      }
      .theme-dark .modal input, .theme-dark .modal select { color-scheme: dark; }
      .modal .row-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
      .modal .row-actions .btn { flex: 0 0 auto; min-width: 90px; }`;
  }

  static getStubConfig() { return {}; }
  static getConfigElement() {
    return document.createElement("worktime-tracker-card-editor");
  }
}

/* Visual editor */
class WorktimeTrackerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) { this._hass = hass; }

  _emit() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config }, bubbles: true, composed: true,
    }));
  }

  _get(key) {
    if (key in this._config) return this._config[key];
    return DEFAULTS[key];
  }

  _render() {
    const sectionRows = SECTIONS.map(([key, label]) => `
      <label class="row">
        <input type="checkbox" data-key="${key}" ${this._get(key) ? "checked" : ""}>
        <span>${label}</span>
      </label>`).join("");

    const theme = this._get("theme") || "auto";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; padding: 8px 0; color: var(--primary-text-color); }
        .group { margin-bottom: 14px; }
        .group-title {
          font-size: 0.85em; font-weight: 600;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 6px;
        }
        .row { display: flex; align-items: center; gap: 10px; padding: 4px 0; cursor: pointer; }
        .row input { transform: scale(1.1); }
        .num-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
        input[type="number"], input[type="text"], select {
          padding: 6px 8px;
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          width: 120px;
        }
        select { width: 160px; }
        .hint { font-size: 0.8em; color: var(--secondary-text-color); margin-top: 8px; }
      </style>
      <div class="group">
        <div class="group-title">Sections</div>
        ${sectionRows}
      </div>
      <div class="group">
        <div class="group-title">Theme</div>
        <div class="num-row">
          <select id="ed-theme">
            <option value="auto" ${theme === "auto" ? "selected" : ""}>Auto (follow sun)</option>
            <option value="light" ${theme === "light" ? "selected" : ""}>Light</option>
            <option value="dark" ${theme === "dark" ? "selected" : ""}>Dark</option>
          </select>
        </div>
        <div class="hint">
          <code>Auto</code> follows <code>sun.sun</code> — dark when the sun is below the horizon.
        </div>
      </div>
      <div class="group">
        <div class="group-title">History rows</div>
        <div class="num-row">
          <input id="ed-limit" type="number" min="1" max="60" value="${this._get("history_limit")}">
        </div>
      </div>
      <div class="group">
        <div class="group-title">Padding (px)</div>
        <div class="num-row">
          <input id="ed-padding" type="number" min="0" max="60" value="${this._get("padding")}">
        </div>
      </div>
      <div class="group">
        <div class="group-title">Max width (px, 0 = fluid)</div>
        <div class="num-row">
          <input id="ed-maxw" type="number" min="0" max="1200" value="${this._get("max_width")}">
        </div>
        <div class="hint">
          Default <code>420</code> (phone-sized). Increase to use more of a wide column. Set <code>0</code> to fill the container.
        </div>
      </div>
      <div class="group">
        <div class="group-title">Entity prefix (multi-instance)</div>
        <div class="num-row">
          <input id="ed-prefix" type="text" placeholder="e.g. home" value="${this._get("entity_prefix") || ""}">
        </div>
        <div class="hint">
          Leave blank for the default instance. Set to e.g. <code>home</code>
          to point at <code>sensor.home_today_hours_today</code>.
        </div>
      </div>
      <div class="hint">
        Theming: override <code>--wt-bg</code>, <code>--wt-card</code>,
        <code>--wt-ink</code>, <code>--wt-accent</code>, <code>--wt-warn</code>
        on <code>:host</code> via card_mod or your theme.
      </div>`;

    this.shadowRoot.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const key = cb.getAttribute("data-key");
        this._config = { ...this._config, [key]: cb.checked };
        this._emit();
      });
    });
    const onNum = (id, key, min = 0) => {
      this.shadowRoot.getElementById(id)?.addEventListener("input", (ev) => {
        const n = parseInt(ev.target.value, 10);
        if (!isNaN(n) && n >= min) {
          this._config = { ...this._config, [key]: n };
          this._emit();
        }
      });
    };
    onNum("ed-limit", "history_limit", 1);
    onNum("ed-padding", "padding", 0);
    onNum("ed-maxw", "max_width", 0);
    this.shadowRoot.getElementById("ed-prefix")?.addEventListener("input", (ev) => {
      const v = (ev.target.value || "").trim().replace(/[^a-z0-9_]/gi, "_");
      this._config = { ...this._config, entity_prefix: v };
      this._emit();
    });
    this.shadowRoot.getElementById("ed-theme")?.addEventListener("change", (ev) => {
      this._config = { ...this._config, theme: ev.target.value };
      this._emit();
    });
  }
}

customElements.define("worktime-tracker-card-editor", WorktimeTrackerCardEditor);
customElements.define("worktime-tracker-card", WorktimeTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worktime-tracker-card",
  name: "Worktime Tracker",
  description: "Phone-first work-time tracker with Today / week / month / history / lookup.",
  preview: false,
  documentationURL: "https://github.com/ottoherdy/worktime-tracker",
});
