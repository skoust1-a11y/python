"""Generate a self-contained HTML evaluation dashboard from benchmark results."""

from __future__ import annotations

import json
from pathlib import Path


DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RAG Evaluation Dashboard — {run_id}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0f1419;
      --surface: #1a2332;
      --border: #2d3a4f;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3b82f6;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem;
    }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
    }}
    .card-label {{ color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card-value {{ font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }}
    .card-value.good {{ color: var(--success); }}
    .card-value.warn {{ color: var(--warning); }}
    .card-value.bad {{ color: var(--danger); }}
    .charts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
    }}
    .chart-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
    }}
    .chart-card h2 {{ font-size: 1rem; margin-bottom: 1rem; color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    tr:hover {{ background: rgba(59, 130, 246, 0.06); }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge.pass {{ background: rgba(34, 197, 94, 0.15); color: var(--success); }}
    .badge.fail {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); }}
  </style>
</head>
<body>
  <h1>RAG Evaluation Dashboard</h1>
  <p class="subtitle">{dataset_name} · Run {run_id} · {generated_at}</p>

  <div class="grid" id="metric-cards"></div>

  <div class="charts">
    <div class="chart-card">
      <h2>RAGAS Quality Metrics</h2>
      <canvas id="ragasChart"></canvas>
    </div>
    <div class="chart-card">
      <h2>Operational Metrics</h2>
      <canvas id="opsChart"></canvas>
    </div>
    <div class="chart-card">
      <h2>Per-Question Scores</h2>
      <canvas id="perQuestionChart"></canvas>
    </div>
  </div>

  <div class="card">
    <h2 style="margin-bottom:1rem;">Detailed Results</h2>
    <table>
      <thead>
        <tr>
          <th>Question</th>
          <th>Context Precision</th>
          <th>Context Recall</th>
          <th>Faithfulness</th>
          <th>Answer Relevancy</th>
          <th>Latency (ms)</th>
          <th>Cost ($)</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody id="results-body"></tbody>
    </table>
  </div>

  <script>
    const data = {payload_json};

    const summary = data.summary;
    const results = data.results;

    function scoreClass(value, threshold = 0.7) {{
      if (value == null) return "";
      return value >= threshold ? "good" : value >= 0.5 ? "warn" : "bad";
    }}

    function fmt(value, digits = 3) {{
      return value == null ? "—" : Number(value).toFixed(digits);
    }}

    const cards = [
      {{ label: "Context Precision", value: summary.avg_context_precision, fmt: 3 }},
      {{ label: "Context Recall", value: summary.avg_context_recall, fmt: 3 }},
      {{ label: "Faithfulness", value: summary.avg_faithfulness, fmt: 3 }},
      {{ label: "Answer Relevancy", value: summary.avg_answer_relevancy, fmt: 3 }},
      {{ label: "Avg Latency (ms)", value: summary.avg_latency_ms, fmt: 1, threshold: null }},
      {{ label: "P95 Latency (ms)", value: summary.p95_latency_ms, fmt: 1, threshold: null }},
      {{ label: "Total Cost ($)", value: summary.total_cost_usd, fmt: 4, threshold: null }},
      {{ label: "Failed Items", value: summary.failed_items, fmt: 0, threshold: null }},
    ];

    document.getElementById("metric-cards").innerHTML = cards.map(c => `
      <div class="card">
        <div class="card-label">${{c.label}}</div>
        <div class="card-value ${{c.threshold != null ? scoreClass(c.value) : ""}}">${{fmt(c.value, c.fmt ?? 3)}}</div>
      </div>
    `).join("");

    const ragasLabels = ["Context Precision", "Context Recall", "Faithfulness", "Answer Relevancy"];
    const ragasValues = [
      summary.avg_context_precision ?? 0,
      summary.avg_context_recall ?? 0,
      summary.avg_faithfulness ?? 0,
      summary.avg_answer_relevancy ?? 0,
    ];

    new Chart(document.getElementById("ragasChart"), {{
      type: "radar",
      data: {{
        labels: ragasLabels,
        datasets: [{{
          label: "Average Score",
          data: ragasValues,
          backgroundColor: "rgba(59, 130, 246, 0.2)",
          borderColor: "#3b82f6",
          pointBackgroundColor: "#3b82f6",
        }}],
      }},
      options: {{
        scales: {{ r: {{ min: 0, max: 1, ticks: {{ stepSize: 0.2 }} }} }},
        plugins: {{ legend: {{ display: false }} }},
      }},
    }});

    new Chart(document.getElementById("opsChart"), {{
      type: "bar",
      data: {{
        labels: ["Avg Latency (ms)", "P95 Latency (ms)", "Total Cost ($)"],
        datasets: [{{
          label: "Operational",
          data: [
            summary.avg_latency_ms ?? 0,
            summary.p95_latency_ms ?? 0,
            (summary.total_cost_usd ?? 0) * 1000,
          ],
          backgroundColor: ["#3b82f6", "#8b5cf6", "#22c55e"],
        }}],
      }},
      options: {{
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => {{
                if (ctx.dataIndex === 2) return `Cost: $${{(summary.total_cost_usd ?? 0).toFixed(4)}}`;
                return `${{ctx.parsed.y.toFixed(1)}} ms`;
              }},
            }},
          }},
        }},
      }},
    }});

    const questionLabels = results.map((_, i) => `Q${{i + 1}}`);
    new Chart(document.getElementById("perQuestionChart"), {{
      type: "bar",
      data: {{
        labels: questionLabels,
        datasets: [
          {{ label: "Faithfulness", data: results.map(r => r.faithfulness ?? 0), backgroundColor: "#3b82f6" }},
          {{ label: "Answer Relevancy", data: results.map(r => r.answer_relevancy ?? 0), backgroundColor: "#22c55e" }},
        ],
      }},
      options: {{
        scales: {{ y: {{ min: 0, max: 1 }} }},
      }},
    }});

    document.getElementById("results-body").innerHTML = results.map(r => `
      <tr>
        <td>${{r.question.slice(0, 80)}}${{r.question.length > 80 ? "…" : ""}}</td>
        <td>${{fmt(r.context_precision)}}</td>
        <td>${{fmt(r.context_recall)}}</td>
        <td>${{fmt(r.faithfulness)}}</td>
        <td>${{fmt(r.answer_relevancy)}}</td>
        <td>${{fmt(r.latency_ms, 1)}}</td>
        <td>${{fmt(r.cost_usd, 4)}}</td>
        <td><span class="badge ${{r.error ? "fail" : "pass"}}">${{r.error ? "FAIL" : "PASS"}}</span></td>
      </tr>
    `).join("");
  </script>
</body>
</html>
"""


def generate_dashboard(
    results_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Generate an HTML dashboard from a saved evaluation JSON file."""
    results_path = Path(results_path)
    payload = json.loads(results_path.read_text(encoding="utf-8"))

    if output_path is None:
        output_path = results_path.with_suffix(".html")
    else:
        output_path = Path(output_path)

    html = DASHBOARD_TEMPLATE.format(
        run_id=payload.get("run_id", "unknown"),
        dataset_name=payload.get("dataset_name", "benchmark"),
        generated_at=payload.get("generated_at", ""),
        payload_json=json.dumps(payload),
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path
