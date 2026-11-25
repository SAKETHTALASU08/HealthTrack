/**
 * api.js — HTTP client for HealthTrack backend endpoints.
 */

import { buildApiErrorMessage } from './utils.js';

/** Error thrown when fetch itself rejects (offline / server down). */
export class NetworkError extends Error {
  constructor(message = 'Unable to reach the server. Check your connection.') {
    super(message);
    this.name = 'NetworkError';
  }
}

/** Error thrown when the server responds with a non-2xx status code. */
export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {number} status
   */
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Perform a JSON fetch and normalize network vs HTTP errors.
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<any>}
 */
async function requestJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new NetworkError();
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw new ApiError(buildApiErrorMessage(body, response.status), response.status);
  }

  return body;
}

/**
 * Fetch symptom logs for a patient, sorted ascending by timestamp.
 * @param {string} patientId
 * @param {string} [days]
 */
export function fetchSymptoms(patientId, days = '') {
  const qs = days ? `?days=${encodeURIComponent(days)}` : '';
  return requestJson(`/api/patients/${encodeURIComponent(patientId)}/symptoms${qs}`);
}

/**
 * Fetch 30-day daily average severity trends.
 * @param {string} patientId
 * @param {number} [days=30]
 */
export function fetchTrends(patientId, days = 30) {
  return requestJson(`/api/patients/${encodeURIComponent(patientId)}/trends?days=${days}`);
}

/**
 * Fetch aggregate insights for a patient.
 * @param {string} patientId
 */
export function fetchInsights(patientId) {
  return requestJson(`/api/patients/${encodeURIComponent(patientId)}/insights`);
}

/**
 * Create a new symptom log entry.
 * @param {{ patient_id: string, description: string, severity: number }} payload
 */
export function postSymptom(payload) {
  return requestJson('/api/symptoms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
