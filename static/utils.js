/**
 * utils.js — Pure helpers, constants, validation, formatting, and safe storage.
 */

export const SEVERITY_MIN = 1;
export const SEVERITY_MAX = 10;
export const DESCRIPTION_MAX_LEN = 500;
export const PATIENT_ID_MAX_LEN = 64;
export const PATIENT_ID_RE = /^[A-Za-z0-9\-_]+$/;

export const STORAGE_KEYS = {
  PATIENT_ID: 'healthtrack_patient_id',
  THEME: 'healthtrack_theme',
};

/**
 * Safely read a key from localStorage.
 * @param {string} key
 * @returns {string|null}
 */
export function storageGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Safely write a key to localStorage.
 * @param {string} key
 * @param {string} value
 */
export function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage errors (e.g., private browsing / quota exceeded)
  }
}

/**
 * Validate a patient ID using the same rules as the backend.
 * @param {string} pid
 * @returns {string|null} Error message or null when valid
 */
export function validatePatientId(pid) {
  if (!pid) return 'Patient ID must not be empty.';
  if (pid.length > PATIENT_ID_MAX_LEN) {
    return `Patient ID must be at most ${PATIENT_ID_MAX_LEN} characters.`;
  }
  if (!PATIENT_ID_RE.test(pid)) {
    return 'Patient ID may only contain letters, digits, hyphens, and underscores.';
  }
  return null;
}

/**
 * Validate symptom description and severity on the client side.
 * @param {string} rawDescription
 * @param {number} severity
 * @returns {{ valid: boolean, descriptionError: string, severityError: string }}
 */
export function validateSymptomForm(rawDescription, severity) {
  const trimmed = rawDescription.trim();
  let descriptionError = '';
  let severityError = '';

  if (!trimmed) {
    descriptionError = 'Description must not be empty or whitespace-only.';
  } else if (trimmed.length > DESCRIPTION_MAX_LEN) {
    descriptionError = `Description must be at most ${DESCRIPTION_MAX_LEN} characters.`;
  }

  if (!Number.isInteger(severity) || severity < SEVERITY_MIN || severity > SEVERITY_MAX) {
    severityError = `Severity must be a whole number between ${SEVERITY_MIN} and ${SEVERITY_MAX}.`;
  }

  return {
    valid: !descriptionError && !severityError,
    descriptionError,
    severityError,
  };
}

/**
 * Format an ISO timestamp as a human-friendly local date-time (e.g. "25 Nov 2026, 3:42 PM").
 * @param {string} isoString
 * @returns {string}
 */
export function formatFriendlyDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;

  const datePart = date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  const timePart = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  return `${datePart}, ${timePart}`;
}

/**
 * Return accessible label and CSS class for a severity value (1-10).
 * @param {number} severity
 * @returns {{ label: string, badgeText: string, className: string }}
 */
export function severityMeta(severity) {
  if (severity <= 3) {
    return { label: 'Mild', badgeText: `${severity} · Mild`, className: 'sev-low' };
  }
  if (severity <= 6) {
    return { label: 'Moderate', badgeText: `${severity} · Moderate`, className: 'sev-medium' };
  }
  return { label: 'Severe', badgeText: `${severity} · Severe`, className: 'sev-high' };
}

/**
 * Extract a human-readable message from an API error payload.
 * @param {object|null} json
 * @param {number} status
 * @returns {string}
 */
export function buildApiErrorMessage(json, status) {
  if (json && Array.isArray(json.details) && json.details.length > 0) {
    return json.details.map((d) => `${d.field}: ${d.message}`).join(' · ');
  }
  if (json && json.error) {
    return json.error;
  }
  return `Server returned status ${status}.`;
}
