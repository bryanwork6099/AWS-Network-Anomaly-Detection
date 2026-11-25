import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;
const THRESHOLD = 2.980612;

function formatNumber(value) {
  return new Intl.NumberFormat().format(value ?? 0);
}

function formatBytes(value) {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  return `${(value / 1024).toFixed(1)} KB`;
}

function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function App() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [filter, setFilter] = useState("ALL");

  async function fetchRecords() {
    try {
      setError("");

      const url = new URL(API_URL);
      url.searchParams.set("limit", "100");

      const result = await fetch(url);
      if (!result.ok) {
        throw new Error(`API request failed: HTTP ${result.status}`);
      }

      const data = await result.json();
      setRecords(data.items ?? []);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "Unable to load network traffic.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRecords();

    const interval = setInterval(fetchRecords, 30000);
    return () => clearInterval(interval);
  }, []);

  const stats = useMemo(() => {
    const anomalies = records.filter(
      (item) => item.anomaly_status === "ANOMALY"
    );

    const normal = records.filter(
      (item) => item.anomaly_status === "NORMAL"
    );

    const sources = new Set(
      records.map((item) => item.PK?.replace("WINDOW#", ""))
    );

    const totalConnections = records.reduce(
      (sum, item) => sum + (item.total_connections ?? 0),
      0
    );

    const anomalyRate = records.length
      ? (anomalies.length / records.length) * 100
      : 0;

    return {
      anomalies,
      normal,
      sources,
      totalConnections,
      anomalyRate,
    };
  }, [records]);

  const filteredRecords = records.filter((item) => {
    if (filter === "ALL") return true;
    return item.anomaly_status === filter;
  });

  const topScore = Math.max(
    THRESHOLD,
    ...records.map((item) => item.anomaly_score ?? 0)
  );

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">N</div>
          <div>
            <h2>NETGUARD</h2>
            <span>SECURITY OPERATIONS</span>
          </div>
        </div>

        <div className="nav-section">WORKSPACE</div>
        <div className="nav-item active">
          <span>◈</span> Overview
        </div>
        <div className="nav-item">
          <span>⌁</span> Network Traffic
        </div>
        <div className="nav-item">
          <span>⚠</span> Threat Detection
        </div>
        <div className="nav-item">
          <span>▤</span> Event History
        </div>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            <div>
              <strong>Pipeline Status</strong>
              <small>Connected to API</small>
            </div>
          </div>
          <div className="sidebar-footer">
            AWS Network Anomaly Detection
            <br />
            Model: rcf-v3
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">WORKSPACE / OVERVIEW</div>
            <h1>Security Overview</h1>
            <p>Real-time network anomaly monitoring and analysis</p>
          </div>

          <div className="topbar-actions">
            <div className="live-indicator">
              <span className="status-dot" />
              LIVE DATA
            </div>
            <button
              className="refresh-button"
              onClick={fetchRecords}
              disabled={loading}
            >
              ↻ Refresh
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            API connection error: {error}
          </div>
        )}

        <section className="metrics-grid">
          <MetricCard
            label="TOTAL WINDOWS"
            value={formatNumber(records.length)}
            detail="Finalized traffic windows"
            icon="▦"
          />
          <MetricCard
            label="TOTAL CONNECTIONS"
            value={formatNumber(stats.totalConnections)}
            detail="Across returned windows"
            icon="⌁"
          />
          <MetricCard
            label="ANOMALOUS WINDOWS"
            value={formatNumber(stats.anomalies.length)}
            detail={`${stats.anomalyRate.toFixed(1)}% of windows`}
            icon="⚠"
            alert
          />
          <MetricCard
            label="MONITORED SOURCES"
            value={formatNumber(stats.sources.size)}
            detail="Unique source IP addresses"
            icon="◎"
          />
        </section>

        <section className="content-grid">
          <div className="panel detection-panel">
            <div className="panel-heading">
              <div>
                <h3>Anomaly Detection</h3>
                <p>Random Cut Forest · Model rcf-v3</p>
              </div>
              <span className="model-tag">MODEL ACTIVE</span>
            </div>

            <div className="score-summary">
              <div>
                <span className="muted-label">DETECTION THRESHOLD</span>
                <strong>{THRESHOLD.toFixed(6)}</strong>
              </div>
              <div>
                <span className="muted-label">HIGHEST OBSERVED SCORE</span>
                <strong className="danger-text">
                  {records.length
                    ? Math.max(
                        ...records.map((item) => item.anomaly_score ?? 0)
                      ).toFixed(4)
                    : "—"}
                </strong>
              </div>
            </div>

            <div className="score-chart">
              {records.length === 0 && !loading ? (
                <p className="empty-state">No scored records available.</p>
              ) : (
                records.map((item, index) => {
                  const score = item.anomaly_score ?? 0;
                  const height = Math.max(
                    4,
                    Math.min(100, (score / topScore) * 100)
                  );

                  return (
                    <div className="score-column" key={`${item.PK}-${item.SK}`}>
                      <div className="score-tooltip">
                        {score.toFixed(3)}
                      </div>
                      <div
                        className={`score-bar ${
                          item.anomaly_status === "ANOMALY"
                            ? "anomaly-bar"
                            : "normal-bar"
                        }`}
                        style={{ height: `${height}%` }}
                        title={`${item.PK}: ${score.toFixed(4)}`}
                      />
                      <span>#{index + 1}</span>
                    </div>
                  );
                })
              )}
            </div>
            <div className="chart-legend">
              <span><i className="legend-normal" /> Normal</span>
              <span><i className="legend-anomaly" /> Anomaly</span>
              <span>Threshold: {THRESHOLD}</span>
            </div>
          </div>

          <div className="panel distribution-panel">
            <div className="panel-heading">
              <div>
                <h3>Detection Distribution</h3>
                <p>Classification of returned windows</p>
              </div>
            </div>

            <div className="distribution-total">
              <strong>{records.length}</strong>
              <span>Total windows</span>
            </div>

            <div className="distribution-row">
              <div className="distribution-label">
                <span>Normal</span>
                <strong>{stats.normal.length}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-normal"
                  style={{
                    width: `${records.length ? (stats.normal.length / records.length) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            <div className="distribution-row">
              <div className="distribution-label">
                <span>Anomaly</span>
                <strong>{stats.anomalies.length}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-anomaly"
                  style={{
                    width: `${records.length ? (stats.anomalies.length / records.length) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            <div className="distribution-footer">
              <span>Classification threshold</span>
              <strong>{THRESHOLD}</strong>
            </div>
          </div>
        </section>

        <section className="panel activity-panel">
          <div className="panel-heading activity-heading">
            <div>
              <h3>Network Activity</h3>
              <p>Finalized and scored traffic windows from DynamoDB</p>
            </div>

            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="filter-select"
            >
              <option value="ALL">All records</option>
              <option value="ANOMALY">Anomalies only</option>
              <option value="NORMAL">Normal only</option>
            </select>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SOURCE IP</th>
                  <th>WINDOW</th>
                  <th>CONNECTIONS</th>
                  <th>FAILED</th>
                  <th>ANOMALY SCORE</th>
                  <th>CLASSIFICATION</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((item) => (
                  <tr key={`${item.PK}-${item.SK}`}>
                    <td className="ip-cell">
                      {item.PK?.replace("WINDOW#", "")}
                    </td>
                    <td>{formatTime(item.window_start)}</td>
                    <td>{formatNumber(item.total_connections)}</td>
                    <td>{formatNumber(item.failed_connections)}</td>
                    <td className="score-cell">
                      {Number(item.anomaly_score ?? 0).toFixed(4)}
                    </td>
                    <td>
                      <span
                        className={`classification ${
                          item.anomaly_status === "ANOMALY"
                            ? "classification-anomaly"
                            : "classification-normal"
                        }`}
                      >
                        {item.anomaly_status ?? "UNSCORED"}
                      </span>
                    </td>
                  </tr>
                ))}

                {!loading && filteredRecords.length === 0 && (
                  <tr>
                    <td colSpan="6" className="empty-state">
                      No matching records found.
                    </td>
                  </tr>
                )}

                {loading && (
                  <tr>
                    <td colSpan="6" className="empty-state">
                      Loading network traffic...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            <span>{filteredRecords.length} records displayed</span>
            <span>
              Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
            </span>
          </div>
        </section>

        <footer className="dashboard-footer">
          <span>NETGUARD · AWS NETWORK ANOMALY DETECTION</span>
          <span>Refresh interval: 30 seconds</span>
        </footer>
      </main>
    </div>
  );
}

function MetricCard({ label, value, detail, icon, alert }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${alert ? "metric-icon-alert" : ""}`}>
        {icon}
      </div>
      <span className="metric-label">{label}</span>
      <strong className={alert ? "danger-text" : ""}>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default App;
