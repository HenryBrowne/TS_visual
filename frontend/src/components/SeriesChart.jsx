import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Legend);

const ANCHOR = new Date("2013-01-01T00:00:00Z");
const ACTUAL_WINDOW = 150;

function toDayOffset(isoTimestamp) {
  return Math.round((new Date(isoTimestamp) - ANCHOR) / 86400000);
}

function fromDayOffset(offset) {
  return new Date(ANCHOR.getTime() + offset * 86400000).toISOString().slice(0, 10);
}

// entries: [{ id, color, actual: [{timestamp,value}], forecast: [{timestamp,value}], forecastLabel }]
export default function SeriesChart({ entries }) {
  const datasets = entries.flatMap(({ id, color, actual, forecast, forecastLabel }) => {
    const recentActual = actual.slice(-ACTUAL_WINDOW);
    const out = [
      {
        label: `${id} actual`,
        data: recentActual.map((p) => ({ x: toDayOffset(p.timestamp), y: p.value })),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.1,
      },
    ];
    if (forecast && forecast.length > 0) {
      out.push({
        label: `${id} forecast (${forecastLabel})`,
        data: forecast.map((p) => ({ x: toDayOffset(p.timestamp), y: p.value })),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 0,
        tension: 0.1,
      });
    }
    return out;
  });

  const options = {
    responsive: true,
    animation: false,
    scales: {
      x: {
        type: "linear",
        ticks: {
          callback: (value) => fromDayOffset(value),
          maxRotation: 0,
        },
        grid: { color: "rgba(128,128,128,0.12)" },
      },
      y: {
        grid: { color: "rgba(128,128,128,0.12)" },
      },
    },
    plugins: {
      legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true } },
      tooltip: {
        callbacks: {
          title: (items) => (items.length ? fromDayOffset(items[0].parsed.x) : ""),
        },
      },
    },
  };

  return <Line data={{ datasets }} options={options} />;
}
