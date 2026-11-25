/**
 * ui.js — DOM rendering, skeleton states, slider UI, alert banners, and toasts.
 * All user-supplied text is inserted via textContent (never innerHTML) to prevent XSS.
 */

import {
  formatFriendlyDateTime,
  severityMeta,
} from './utils.js';

const TOAST_AUTO_DISMISS_MS = 5000;

/**
 * Collect DOM element references used across the UI.
 */
export function getDomRefs() {
  return {
    patientForm: document.getElementById('patient-form'),
    patientInput: document.getElementById('patient-id-input'),
    themeToggle: document.getElementById('theme-toggle'),

    alertBanner: document.getElementById('alert-banner'),
    alertBannerText: document.getElementById('alert-banner-text'),
    alertRetryBtn: document.getElementById('alert-retry-btn'),
    alertCloseBtn: document.getElementById('alert-close-btn'),
    toastContainer: document.getElementById('toast-container'),

    statsSkeleton: document.getElementById('stats-skeleton'),
    statsGrid: document.getElementById('stats-grid'),
    statTotal: document.getElementById('stat-total'),
    statAvg: document.getElementById('stat-avg'),
    statHighest: document.getElementById('stat-highest'),
    statHighestDate: document.getElementById('stat-highest-date'),
    statTrend: document.getElementById('stat-trend'),
    statTrendMeta: document.getElementById('stat-trend-meta'),

    symptomForm: document.getElementById('symptom-form'),
    descInput: document.getElementById('description-input'),
    descCount: document.getElementById('desc-count'),
    descError: document.getElementById('description-error'),
    severityInput: document.getElementById('severity-input'),
    severityBubble: document.getElementById('severity-bubble'),
    severityPill: document.getElementById('severity-pill'),
    severityError: document.getElementById('severity-error'),
    submitBtn: document.getElementById('submit-btn'),
    submitLabel: document.getElementById('submit-label'),
    submitSpinner: document.getElementById('submit-spinner'),

    chartSkeleton: document.getElementById('chart-skeleton'),
    chartEmpty: document.getElementById('chart-empty'),
    chartWrapper: document.getElementById('chart-wrapper'),
    trendCanvas: document.getElementById('trend-chart'),

    searchInput: document.getElementById('search-input'),
    daysFilter: document.getElementById('days-filter'),
    logsSkeleton: document.getElementById('logs-skeleton'),
    logsEmpty: document.getElementById('logs-empty'),
    logsEmptyTitle: document.getElementById('logs-empty-title'),
    logsEmptyMsg: document.getElementById('logs-empty-msg'),
    emptyCtaBtn: document.getElementById('empty-cta-btn'),
    tableScroll: document.getElementById('table-scroll'),
    logsTbody: document.getElementById('logs-tbody'),
  };
}

/**
 * Show or hide loading skeletons for stats, chart, and table.
 * @param {ReturnType<getDomRefs>} dom
 * @param {boolean} loading
 */
export function setDashboardLoading(dom, loading) {
  dom.statsSkeleton.classList.toggle('hidden', !loading);
  dom.statsGrid.classList.toggle('hidden', loading);

  dom.chartSkeleton.classList.toggle('hidden', !loading);
  if (loading) {
    dom.chartEmpty.classList.add('hidden');
    dom.chartWrapper.classList.add('hidden');
  }

  dom.logsSkeleton.classList.toggle('hidden', !loading);
  if (loading) {
    dom.logsEmpty.classList.add('hidden');
    dom.tableScroll.classList.add('hidden');
  }
}

/**
 * Toggle submit button spinner and disabled state.
 * @param {ReturnType<getDomRefs>} dom
 * @param {boolean} submitting
 */
export function setFormSubmitting(dom, submitting) {
  dom.submitBtn.disabled = submitting;
  dom.submitLabel.textContent = submitting ? 'Logging…' : 'Log Symptom';
  dom.submitSpinner.classList.toggle('hidden', !submitting);
}

/**
 * Sync the severity slider bubble position, pill badge, and ARIA attributes.
 * @param {ReturnType<getDomRefs>} dom
 */
export function updateSeveritySliderUI(dom) {
  const val = Number.parseInt(dom.severityInput.value, 10);
  const meta = severityMeta(val);

  dom.severityBubble.textContent = String(val);
  const percent = ((val - 1) / 9) * 100;
  // Offset slightly to keep bubble centered over thumb across full range
  dom.severityBubble.style.left = `calc(${percent}% + (${8 - percent * 0.16}px))`;

  dom.severityPill.className = `severity-badge ${meta.className}`;
  dom.severityPill.textContent = meta.badgeText;

  dom.severityInput.setAttribute('aria-valuenow', String(val));
  dom.severityInput.setAttribute('aria-valuetext', `${val} out of 10, ${meta.label}`);
}

/**
 * Display inline field errors on the symptom form.
 * @param {ReturnType<getDomRefs>} dom
 * @param {string} descErr
 * @param {string} sevErr
 */
export function setFormFieldErrors(dom, descErr, sevErr) {
  dom.descError.textContent = descErr;
  dom.descInput.classList.toggle('input-invalid', Boolean(descErr));
  dom.severityError.textContent = sevErr;
}

/**
 * Render the 4 summary stat cards from /insights response.
 * @param {ReturnType<getDomRefs>} dom
 * @param {object} data
 */
export function renderStats(dom, data) {
  dom.statTotal.textContent = String(data.total_entries ?? 0);
  dom.statAvg.textContent =
    data.overall_average_severity !== null && data.overall_average_severity !== undefined
      ? data.overall_average_severity.toFixed(1)
      : '–';

  const high = data.highest_severity_entry;
  if (high) {
    dom.statHighest.textContent = `${high.severity} / 10`;
    dom.statHighestDate.textContent = formatFriendlyDateTime(high.timestamp);
  } else {
    dom.statHighest.textContent = '–';
    dom.statHighestDate.textContent = 'No peak recorded';
  }

  dom.statTrend.className = 'stat-value stat-trend';
  const dir = data.trend_direction;
  if (dir === 'up') {
    dom.statTrend.textContent = '▲ Worse';
    dom.statTrend.classList.add('trend-up');
  } else if (dir === 'down') {
    dom.statTrend.textContent = '▼ Improving';
    dom.statTrend.classList.add('trend-down');
  } else if (dir === 'stable') {
    dom.statTrend.textContent = '→ Stable';
    dom.statTrend.classList.add('trend-flat');
  } else {
    dom.statTrend.textContent = '–';
    dom.statTrend.classList.add('trend-flat');
  }
}

/**
 * Render the symptom history table (oldest at top, latest at bottom).
 * @param {ReturnType<getDomRefs>} dom
 * @param {Array<object>} logs
 * @param {{ searchTerm?: string, highlightId?: number|null }} [options]
 */
export function renderSymptomTable(dom, logs, { searchTerm = '', highlightId = null } = {}) {
  const query = searchTerm.trim().toLowerCase();
  const filtered = query
    ? logs.filter((item) => item.description.toLowerCase().includes(query))
    : logs;

  dom.logsTbody.textContent = '';

  if (filtered.length === 0) {
    dom.tableScroll.classList.add('hidden');
    dom.logsEmpty.classList.remove('hidden');

    if (logs.length > 0 && query) {
      dom.logsEmptyTitle.textContent = 'No matching symptoms';
      dom.logsEmptyMsg.textContent = `No entries match "${searchTerm}". Try clearing your search.`;
      dom.emptyCtaBtn.classList.add('hidden');
    } else {
      dom.logsEmptyTitle.textContent = 'No symptoms logged yet';
      dom.logsEmptyMsg.textContent =
        'Record your first symptom using the form above to start tracking.';
      dom.emptyCtaBtn.classList.remove('hidden');
    }
    return;
  }

  dom.logsEmpty.classList.add('hidden');
  dom.tableScroll.classList.remove('hidden');

  let highlightedRow = null;

  filtered.forEach((log, idx) => {
    const tr = document.createElement('tr');
    if (highlightId !== null && log.id === highlightId) {
      tr.classList.add('row-highlight');
      highlightedRow = tr;
    }

    const tdNum = document.createElement('td');
    tdNum.className = 'col-num';
    tdNum.textContent = String(idx + 1);
    tr.appendChild(tdNum);

    const tdTime = document.createElement('td');
    tdTime.className = 'col-time';
    tdTime.textContent = formatFriendlyDateTime(log.timestamp);
    tdTime.title = log.timestamp;
    tr.appendChild(tdTime);

    const tdDesc = document.createElement('td');
    tdDesc.className = 'col-desc';
    tdDesc.textContent = log.description;
    tr.appendChild(tdDesc);

    const tdSev = document.createElement('td');
    tdSev.className = 'col-sev';
    const meta = severityMeta(log.severity);
    const pill = document.createElement('span');
    pill.className = `severity-badge ${meta.className}`;
    pill.textContent = meta.badgeText;
    tdSev.appendChild(pill);
    tr.appendChild(tdSev);

    dom.logsTbody.appendChild(tr);
  });

  if (highlightedRow) {
    dom.tableScroll.scrollTo({
      top: dom.tableScroll.scrollHeight,
      behavior: 'smooth',
    });
  }
}

/**
 * Show the inline alert banner (for persistent / validation / network errors).
 * @param {ReturnType<getDomRefs>} dom
 * @param {string} message
 * @param {Function|null} [onRetry]
 */
export function showAlertBanner(dom, message, onRetry = null) {
  dom.alertBannerText.textContent = message;
  dom.alertBanner.classList.remove('hidden');
  if (onRetry) {
    dom.alertRetryBtn.classList.remove('hidden');
    dom.alertRetryBtn.onclick = () => {
      hideAlertBanner(dom);
      onRetry();
    };
  } else {
    dom.alertRetryBtn.classList.add('hidden');
    dom.alertRetryBtn.onclick = null;
  }
}

/**
 * Hide the inline alert banner.
 * @param {ReturnType<getDomRefs>} dom
 */
export function hideAlertBanner(dom) {
  dom.alertBanner.classList.add('hidden');
  dom.alertBannerText.textContent = '';
}

/**
 * Show a non-blocking top-right toast notification.
 * @param {ReturnType<getDomRefs>} dom
 * @param {{ type: 'success'|'error', message: string, onRetry?: Function|null }} opts
 */
export function showToast(dom, { type, message, onRetry = null }) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');

  const body = document.createElement('div');
  body.className = 'toast-body';

  const text = document.createElement('span');
  text.textContent = message;
  body.appendChild(text);

  if (onRetry) {
    const actions = document.createElement('div');
    actions.className = 'toast-actions';
    const retryBtn = document.createElement('button');
    retryBtn.type = 'button';
    retryBtn.className = 'btn btn-xs btn-secondary';
    retryBtn.textContent = 'Retry';
    retryBtn.addEventListener('click', () => {
      toast.remove();
      onRetry();
    });
    actions.appendChild(retryBtn);
    body.appendChild(actions);
  }

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'icon-btn-sm';
  closeBtn.setAttribute('aria-label', 'Dismiss notification');
  closeBtn.textContent = '✕';
  closeBtn.addEventListener('click', () => toast.remove());

  toast.appendChild(body);
  toast.appendChild(closeBtn);
  dom.toastContainer.appendChild(toast);

  if (!onRetry) {
    window.setTimeout(() => {
      if (toast.isConnected) toast.remove();
    }, TOAST_AUTO_DISMISS_MS);
  }
}
