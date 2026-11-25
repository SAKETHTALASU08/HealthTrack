/**
 * app.js — HealthTrack application entrypoint (ES module).
 */

import {
  NetworkError,
  fetchInsights,
  fetchSymptoms,
  fetchTrends,
  postSymptom,
} from './api.js';
import {
  isDarkModeActive,
  refreshChartTheme,
  renderTrendChart,
} from './chart.js';
import {
  getDomRefs,
  hideAlertBanner,
  renderStats,
  renderSymptomTable,
  setDashboardLoading,
  setFormFieldErrors,
  setFormSubmitting,
  showAlertBanner,
  showToast,
  updateSeveritySliderUI,
} from './ui.js';
import {
  STORAGE_KEYS,
  storageGet,
  storageSet,
  validatePatientId,
  validateSymptomForm,
} from './utils.js';

const dom = getDomRefs();

const state = {
  patientId: '',
  logs: [],
  lastInsertedId: null,
};

/* ── Theme Management ────────────────────────────────────────────────────── */

function initTheme() {
  const saved = storageGet(STORAGE_KEYS.THEME);
  if (saved === 'dark' || saved === 'light') {
    document.documentElement.setAttribute('data-theme', saved);
  }
  syncThemeButton();
}

function syncThemeButton() {
  const dark = isDarkModeActive();
  dom.themeToggle.setAttribute('aria-pressed', String(dark));
}

dom.themeToggle.addEventListener('click', () => {
  const next = isDarkModeActive() ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  storageSet(STORAGE_KEYS.THEME, next);
  syncThemeButton();
  refreshChartTheme();
});

if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    syncThemeButton();
    refreshChartTheme();
  });
}

/* ── Data Loading ────────────────────────────────────────────────────────── */

async function loadPatientDashboard({ highlightId = null } = {}) {
  if (!state.patientId) return;

  hideAlertBanner(dom);
  setDashboardLoading(dom, true);

  try {
    const days = dom.daysFilter.value;
    const [logs, trendsRes, insights] = await Promise.all([
      fetchSymptoms(state.patientId, days),
      fetchTrends(state.patientId, 30),
      fetchInsights(state.patientId),
    ]);

    state.logs = logs;
    state.lastInsertedId = highlightId;

    renderStats(dom, insights);
    renderSymptomTable(dom, state.logs, {
      searchTerm: dom.searchInput.value,
      highlightId,
    });

    if (trendsRes.trends && trendsRes.trends.length > 0) {
      dom.chartEmpty.classList.add('hidden');
      dom.chartWrapper.classList.remove('hidden');
      renderTrendChart(dom.trendCanvas, trendsRes.trends);
    } else {
      dom.chartWrapper.classList.add('hidden');
      dom.chartEmpty.classList.remove('hidden');
    }
  } catch (err) {
    const retryFn = () => loadPatientDashboard({ highlightId });
    if (err instanceof NetworkError) {
      showAlertBanner(dom, err.message, retryFn);
      showToast(dom, { type: 'error', message: err.message, onRetry: retryFn });
    } else {
      showAlertBanner(dom, err.message);
      showToast(dom, { type: 'error', message: err.message });
    }
  } finally {
    setDashboardLoading(dom, false);
  }
}

/* ── Event Handlers ──────────────────────────────────────────────────────── */

dom.patientForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const pid = dom.patientInput.value.trim();
  const err = validatePatientId(pid);
  if (err) {
    showAlertBanner(dom, err);
    showToast(dom, { type: 'error', message: err });
    dom.patientInput.focus();
    return;
  }
  state.patientId = pid;
  storageSet(STORAGE_KEYS.PATIENT_ID, pid);
  loadPatientDashboard();
});

dom.alertCloseBtn.addEventListener('click', () => hideAlertBanner(dom));

dom.severityInput.addEventListener('input', () => updateSeveritySliderUI(dom));

dom.descInput.addEventListener('input', () => {
  dom.descCount.textContent = String(dom.descInput.value.length);
  if (dom.descError.textContent) {
    setFormFieldErrors(dom, '', '');
  }
});

// Ctrl/Cmd + Enter submits the symptom form
dom.descInput.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    dom.symptomForm.requestSubmit();
  }
});

dom.symptomForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlertBanner(dom);

  if (!state.patientId) {
    const msg = 'Enter a Patient ID in the top bar and click Load first.';
    showAlertBanner(dom, msg);
    showToast(dom, { type: 'error', message: msg });
    dom.patientInput.focus();
    return;
  }

  const severity = Number.parseInt(dom.severityInput.value, 10);
  const validation = validateSymptomForm(dom.descInput.value, severity);
  setFormFieldErrors(dom, validation.descriptionError, validation.severityError);
  if (!validation.valid) return;

  const payload = {
    patient_id: state.patientId,
    description: dom.descInput.value.trim(),
    severity,
  };

  setFormSubmitting(dom, true);
  try {
    const res = await postSymptom(payload);
    showToast(dom, {
      type: 'success',
      message: res.message || 'Symptom logged successfully.',
    });

    // Reset form only on success (preserve input on failure)
    dom.descInput.value = '';
    dom.descCount.textContent = '0';
    dom.severityInput.value = '5';
    updateSeveritySliderUI(dom);
    setFormFieldErrors(dom, '', '');

    await loadPatientDashboard({ highlightId: res.data?.id ?? null });
  } catch (err) {
    if (err instanceof NetworkError) {
      const retrySubmit = () => dom.symptomForm.requestSubmit();
      showAlertBanner(dom, err.message, retrySubmit);
      showToast(dom, { type: 'error', message: err.message, onRetry: retrySubmit });
    } else {
      showAlertBanner(dom, err.message);
      showToast(dom, { type: 'error', message: err.message });
    }
  } finally {
    setFormSubmitting(dom, false);
  }
});

dom.daysFilter.addEventListener('change', () => {
  loadPatientDashboard();
});

dom.searchInput.addEventListener('input', () => {
  renderSymptomTable(dom, state.logs, {
    searchTerm: dom.searchInput.value,
    highlightId: null,
  });
});

dom.emptyCtaBtn.addEventListener('click', () => {
  dom.descInput.focus();
});

/* ── Bootstrap ───────────────────────────────────────────────────────────── */

initTheme();
updateSeveritySliderUI(dom);

const savedPatientId = storageGet(STORAGE_KEYS.PATIENT_ID);
if (savedPatientId && !validatePatientId(savedPatientId)) {
  state.patientId = savedPatientId;
  dom.patientInput.value = savedPatientId;
  loadPatientDashboard();
}
