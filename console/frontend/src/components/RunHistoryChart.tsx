import { BarElement, CategoryScale, Chart, Legend, LinearScale, Tooltip } from "chart.js";
import { useMemo } from "react";
import { Bar } from "react-chartjs-2";

import type { Run } from "../api/types";
import { formatMoney, formatShortDay } from "../lib/format";
import { costByDay, SERIES_LABELS, type Series, usedSeries } from "../lib/runHistory";

Chart.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip);

// Read the theme tokens so the chart follows light and dark mode with the page.
const token = (name: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888780";

const SERIES_TOKENS: Record<Series, string> = {
  scan: "--color-series-scan",
  build: "--color-series-build",
  report: "--color-series-report",
  other: "--color-series-other",
};

const RunHistoryChart = ({ runs }: { runs: Run[] }) => {
  const days = useMemo(() => costByDay(runs), [runs]);
  const series = useMemo(() => usedSeries(days), [days]);
  if (days.length === 0) {
    return <p className="text-sm text-muted">No runs in the cost logs yet.</p>;
  }
  const ink = token("--color-muted");
  const data = {
    labels: days.map((d) => formatShortDay(d.day)),
    datasets: series.map((s) => ({
      label: SERIES_LABELS[s],
      data: days.map((d) => Math.round(d.cost[s] * 100) / 100),
      backgroundColor: token(SERIES_TOKENS[s]),
    })),
  };
  return (
    <div className="relative h-56" role="img" aria-label="Model cost per run day, split by stage">
      <Bar
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: ink, boxWidth: 10 } },
            tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${formatMoney(c.parsed.y)}` } },
          },
          scales: {
            x: { stacked: true, ticks: { color: ink }, grid: { display: false } },
            y: {
              stacked: true,
              ticks: { color: ink, callback: (v) => `$${v}` },
              grid: { color: token("--color-line") },
            },
          },
        }}
      />
    </div>
  );
};

export default RunHistoryChart;
