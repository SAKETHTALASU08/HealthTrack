/**
 * chart.js — Chart.js 30-day severity trend line chart with dark-mode support.
 */

let chartInstance = null;

/**
 * Detect whether dark mode is currently active.
 * @returns {boolean}
 */
export function isDarkModeActive() {
  const explicit = document.documentElement.getAttribute('data-theme');
  if (explicit === 'dark') return true;
  if (explicit === 'light') return false;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Build theme-aware colors for Chart.js.
 */
function getThemeColors() {
  const dark = isDarkModeActive();
  return {
    line: dark ? '#2dd4bf' : '#0d9488',
    fillTop: dark ? 'rgba(45, 212, 191, 0.28)' : 'rgba(13, 148, 136, 0.22)',
    fillBottom: dark ? 'rgba(45, 212, 191, 0.0)' : 'rgba(13, 148, 136, 0.0)',
    pointBg: dark ? '#111827' : '#ffffff',
    grid: dark ? 'rgba(148, 163, 184, 0.14)' : 'rgba(15, 23, 42, 0.07)',
    text: dark ? '#94a3b8' : '#64748b',
    tooltipBg: dark ? '#1e293b' : '#0f172a',
  };
}

/**
 * Create a vertical linear gradient under the trend line.
 * @param {CanvasRenderingContext2D} ctx
 * @param {{ fillTop: string, fillBottom: string }} colors
 */
function createAreaGradient(ctx, colors) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, colors.fillTop);
  gradient.addColorStop(1, colors.fillBottom);
  return gradient;
}

/**
 * Render or update the 30-day severity trend chart.
 * @param {HTMLCanvasElement} canvas
 * @param {Array<{ date: string, average_severity: number, entry_count: number }>} trends
 */
export function renderTrendChart(canvas, trends) {
  if (typeof window.Chart === 'undefined') return;

  const ctx = canvas.getContext('2d');
  const colors = getThemeColors();
  const labels = trends.map((t) => t.date);
  const values = trends.map((t) => t.average_severity);
  const counts = trends.map((t) => t.entry_count);

  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets[0].data = values;
    chartInstance.data.datasets[0].entryCounts = counts;
    applyThemeToChart(chartInstance, ctx, colors);
    chartInstance.update();
    return;
  }

  chartInstance = new window.Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Average Severity',
          data: values,
          entryCounts: counts,
          borderColor: colors.line,
          backgroundColor: createAreaGradient(ctx, colors),
          borderWidth: 2.5,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: colors.pointBg,
          pointBorderColor: colors.line,
          pointBorderWidth: 2,
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          title: { display: true, text: 'Date (UTC)', color: colors.text },
          ticks: { color: colors.text, maxTicksLimit: 8 },
          grid: { display: false },
        },
        y: {
          title: { display: true, text: 'Severity (0–10)', color: colors.text },
          min: 0,
          max: 10,
          ticks: { stepSize: 2, color: colors.text },
          grid: { color: colors.grid },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: colors.tooltipBg,
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (context) => {
              const count = context.dataset.entryCounts?.[context.dataIndex];
              const suffix = count ? ` (${count} ${count === 1 ? 'log' : 'logs'})` : '';
              return `Avg. Severity: ${context.parsed.y}${suffix}`;
            },
          },
        },
      },
    },
  });
}

/**
 * Update chart colors when dark/light mode changes.
 */
export function refreshChartTheme() {
  if (!chartInstance) return;
  const colors = getThemeColors();
  applyThemeToChart(chartInstance, chartInstance.ctx, colors);
  chartInstance.update();
}

function applyThemeToChart(chart, ctx, colors) {
  const ds = chart.data.datasets[0];
  ds.borderColor = colors.line;
  ds.backgroundColor = createAreaGradient(ctx, colors);
  ds.pointBackgroundColor = colors.pointBg;
  ds.pointBorderColor = colors.line;

  chart.options.scales.x.title.color = colors.text;
  chart.options.scales.x.ticks.color = colors.text;
  chart.options.scales.y.title.color = colors.text;
  chart.options.scales.y.ticks.color = colors.text;
  chart.options.scales.y.grid.color = colors.grid;
  chart.options.plugins.tooltip.backgroundColor = colors.tooltipBg;
}
