import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;
const THRESHOLD = 2.980612;
const REFRESH_INTERVAL = 30000;

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value) || 0);
}

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function getSource(item) {
  return item.PK?.replace("WINDOW#", "") || "Unknown";
}

function getWindowKey(item) {
  return `${item.PK || ""}-${item.SK || ""}`;
}

function getSeverity(score) {
  if (score >= THRESHOLD * 2) return "CRITICAL";
  if (score >= THRESHOLD) return "HIGH";
  if (score >= THRESHOLD * 0.7) return "ELEVATED";
  return "NORMAL";
}

function App() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [activeView, setActiveView] = useState("overview");

  const fetchRecords = useCallback(async (manual = false) => {
    if (!API_URL) {
      setError("VITE_API_URL is not configured.");
      setLoading(false);
      return;
    }

    if (manual) setRefreshing(true);

    try {
      const url = new URL(API_URL);
      url.searchParams.set("limit", "100");

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`API request failed: HTTP ${response.status}`);
      }

      const data = await response.json();
      const items = Array.isArray(data.items) ? data.items : [];

      setRecords(items);
      setLastUpdated(new Date());
      setError("");
    } catch (err) {
      setError(err.message || "Unable to load network traffic.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchRecords();

    const interval = setInterval(() => {
      fetchRecords();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchRecords]);

  const stats = useMemo(() => {
    const anomalies = records.filter(
      (item) => item.anomaly_status === "ANOMALY"
    );

    const normal = records.filter(
      (item) => item.anomaly_status === "NORMAL"
    );

    const sources = new Set(records.map(getSource));

    const totalConnections = records.reduce(
      (sum, item) => sum + Number(item.total_connections || 0),
      0
    );

    const failedConnections = records.reduce(
      (sum, item) => sum + Number(item.failed_connections || 0),
      0
    );

    const totalBytes = records.reduce(
      (sum, item) =>
        sum +
        Number(item.bytes_sent || 0) +
        Number(item.bytes_received || 0),
      0
    );

    const anomalyRate = records.length
      ? (anomalies.length / records.length) * 100
      : 0;

    const tcp = records.reduce(
      (sum, item) => sum + Number(item.tcp_connections || 0),
      0
    );

    const udp = records.reduce(
      (sum, item) => sum + Number(item.udp_connections || 0),
      0
    );

    const highestScore = records.reduce(
      (max, item) => Math.max(max, Number(item.anomaly_score || 0)),
      0
    );

    return {
      anomalies,
      normal,
      sources,
      totalConnections,
      failedConnections,
      totalBytes,
      anomalyRate,
      tcp,
      udp,
      highestScore,
    };
  }, [records]);

  const sortedRecords = useMemo(() => {
    return [...records].sort((a, b) => {
      const timeA = new Date(a.window_start || 0).getTime() || 0;
      const timeB = new Date(b.window_start || 0).getTime() || 0;
      return timeB - timeA;
    });
  }, [records]);

  const filteredRecords = useMemo(() => {
    return sortedRecords.filter((item) => {
      const matchesFilter =
        filter === "ALL" || item.anomaly_status === filter;

      const searchText = search.trim().toLowerCase();
      const matchesSearch =
        !searchText ||
        [
          getSource(item),
          item.destination_ip,
          item.anomaly_status,
          item.model_version,
          item.SK,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(searchText));

      return matchesFilter && matchesSearch;
    });
  }, [sortedRecords, filter, search]);

  const topSources = useMemo(() => {
    const grouped = new Map();

    records.forEach((item) => {
      const source = getSource(item);
      const current = grouped.get(source) || {
        source,
        connections: 0,
        anomalies: 0,
      };

      current.connections += Number(item.total_connections || 0);

      if (item.anomaly_status === "ANOMALY") {
        current.anomalies += 1;
      }

      grouped.set(source, current);
    });

    return [...grouped.values()]
      .sort((a, b) => b.connections - a.connections)
      .slice(0, 5);
  }, [records]);

  const chartRecords = useMemo(
    () => [...sortedRecords].reverse().slice(-20),
    [sortedRecords]
  );

  const chartMax = Math.max(
    THRESHOLD * 1.2,
    ...chartRecords.map((item) => Number(item.anomaly_score || 0))
  );

  const normalPercentage = records.length
    ? (stats.normal.length / records.length) * 100
    : 0;

  const anomalyPercentage = records.length
    ? (stats.anomalies.length / records.length) * 100
    : 0;

  function openView(view) {
    setActiveView(view);
    if (view === "threats") setFilter("ANOMALY");
    else setFilter("ALL");
  }

  return (
    <div className="soc-shell">
      <aside className="soc-sidebar">
        <div className="soc-brand">
          <div className="soc-brand-mark">
            <svg viewBox="0 0 40 40" aria-hidden="true">
              <path d="M20 3 34 9v10c0 9-5.8 14.7-14 18C11.8 33.7 6 28 6 19V9l14-6Z" />
              <path d="m13 20 5 5 10-11" />
            </svg>
          </div>
          <div>
            <div className="soc-brand-name">NETGUARD</div>
            <div className="soc-brand-subtitle">SECURITY OPERATIONS</div>
          </div>
        </div>

        <div className="soc-nav-label">MONITORING</div>

        <button
          className={`soc-nav-item ${activeView === "overview" ? "active" : ""}`}
          onClick={() => openView("overview")}
        >
          <span className="soc-nav-icon">◈</span>
          Security Overview
        </button>

        <button
          className={`soc-nav-item ${activeView === "traffic" ? "active" : ""}`}
          onClick={() => openView("traffic")}
        >
          <span className="soc-nav-icon">⌁</span>
          Network Traffic
        </button>

        <button
          className={`soc-nav-item ${activeView === "threats" ? "active" : ""}`}
          onClick={() => openView("threats")}
        >
          <span className="soc-nav-icon">⌖</span>
          Threat Detection
          {stats.anomalies.length > 0 && (
            <span className="soc-nav-count">{stats.anomalies.length}</span>
          )}
        </button>

        <button
          className={`soc-nav-item ${activeView === "events" ? "active" : ""}`}
          onClick={() => openView("events")}
        >
          <span className="soc-nav-icon">▤</span>
          Event History
        </button>

        <div className="soc-sidebar-bottom">
          <div className="soc-pipeline-card">
            <div className="soc-pipeline-heading">
              <span className={`soc-status-dot ${error ? "offline" : ""}`} />
              PIPELINE STATUS
            </div>
            <strong>{error ? "Connection issue" : loading ? "Connecting..." : "API connected"}</strong>
            <span>API Gateway · DynamoDB</span>
            <div className="soc-pipeline-line">
              <span />
            </div>
          </div>

          <div className="soc-sidebar-meta">
            AWS NETWORK ANOMALY DETECTION
            <br />
            MODEL VERSION: RCF-V3
            <br />
            REGION: AP-SOUTHEAST-1
          </div>
        </div>
      </aside>

      <main className="soc-main">
        <header className="soc-topbar">
          <div className="soc-breadcrumb">
            SECURITY OPERATIONS <span>/</span>{" "}
            {activeView.replace("-", " ").toUpperCase()}
          </div>

          <div className="soc-topbar-right">
            <div className="soc-live-status">
              <span className={`soc-status-dot ${error ? "offline" : ""}`} />
              {error ? "API ISSUE" : loading ? "CONNECTING" : "MONITORING"}
            </div>

            <div className="soc-refresh-info">
              <span>LAST UPDATE</span>
              <strong>
                {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
              </strong>
            </div>

            <button
              className="soc-refresh-button"
              onClick={() => fetchRecords(true)}
              disabled={refreshing}
            >
              <span className={refreshing ? "soc-spinning" : ""}>↻</span>
              {refreshing ? "Refreshing" : "Refresh"}
            </button>
          </div>
        </header>

        <div className="soc-page-heading">
          <div>
            <div className="soc-eyebrow">NETWORK SECURITY INTELLIGENCE</div>
            <h1>
              {activeView === "threats"
                ? "Threat Detection"
                : activeView === "traffic"
                  ? "Network Traffic"
                  : activeView === "events"
                    ? "Security Event History"
                    : "Security Overview"}
            </h1>
            <p>
              Monitor network behavior, identify anomalies and investigate
              suspicious activity.
            </p>
          </div>
          <div className="soc-model-status">
            <span className="soc-model-icon">◈</span>
            <div>
              <span>DETECTION ENGINE</span>
              <strong>Random Cut Forest</strong>
              <small>Model rcf-v3 · Active</small>
            </div>
          </div>
        </div>

        {error && (
          <div className="soc-error-banner">
            <span>!</span>
            <div>
              <strong>API connection error</strong>
              <p>{error}</p>
            </div>
            <button onClick={() => fetchRecords(true)}>Retry</button>
          </div>
        )}

        <section className="soc-metrics-grid">
          <MetricCard
            label="TRAFFIC WINDOWS"
            value={formatNumber(records.length)}
            detail="Finalized and scored windows"
            icon="▦"
            accent="blue"
          />
          <MetricCard
            label="TOTAL CONNECTIONS"
            value={formatNumber(stats.totalConnections)}
            detail="Across returned windows"
            icon="⌁"
            accent="cyan"
          />
          <MetricCard
            label="DETECTED ANOMALIES"
            value={formatNumber(stats.anomalies.length)}
            detail={`${stats.anomalyRate.toFixed(1)}% of returned windows`}
            icon="⚠"
            accent="red"
          />
          <MetricCard
            label="FAILED CONNECTIONS"
            value={formatNumber(stats.failedConnections)}
            detail="Across returned windows"
            icon="⊘"
            accent="orange"
          />
        </section>

        <section className="soc-analytics-grid">
          <div className="soc-panel soc-score-panel">
            <div className="soc-panel-header">
              <div>
                <div className="soc-panel-kicker">MACHINE LEARNING</div>
                <h2>Anomaly Score Analysis</h2>
                <p>Observed Random Cut Forest inference scores</p>
              </div>
              <span className="soc-active-tag">
                <i /> MODEL ACTIVE
              </span>
            </div>

            <div className="soc-chart-summary">
              <div>
                <span>DETECTION THRESHOLD</span>
                <strong>{THRESHOLD.toFixed(6)}</strong>
              </div>
              <div>
                <span>HIGHEST SCORE</span>
                <strong className="soc-danger-text">
                  {records.length ? stats.highestScore.toFixed(4) : "—"}
                </strong>
              </div>
              <div>
                <span>MODEL VERSION</span>
                <strong>RCF-V3</strong>
              </div>
            </div>

            <div className="soc-score-chart">
              {chartRecords.length === 0 ? (
                <div className="soc-chart-empty">
                  {loading ? "Loading anomaly scores..." : "No scored records available."}
                </div>
              ) : (
                <>
                  <div className="soc-threshold-line">
                    <span>THRESHOLD {THRESHOLD}</span>
                  </div>
                  <div className="soc-bars">
                    {chartRecords.map((item, index) => {
                      const score = Number(item.anomaly_score || 0);
                      const height = Math.max(3, (score / chartMax) * 100);
                      const isAnomaly = item.anomaly_status === "ANOMALY";

                      return (
                        <button
                          className={`soc-bar-column ${isAnomaly ? "is-anomaly" : ""}`}
                          key={getWindowKey(item)}
                          onClick={() => setSelectedRecord(item)}
                          title={`${getSource(item)} · Score ${score.toFixed(4)}`}
                        >
                          <span className="soc-bar-value">{score.toFixed(2)}</span>
                          <span
                            className="soc-score-bar"
                            style={{ height: `${height}%` }}
                          />
                          <span className="soc-bar-label">{index + 1}</span>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>

            <div className="soc-chart-legend">
              <span><i className="legend-normal" /> NORMAL</span>
              <span><i className="legend-anomaly" /> ANOMALY</span>
              <span className="soc-legend-threshold">Threshold: {THRESHOLD}</span>
            </div>
          </div>

          <div className="soc-panel soc-distribution-panel">
            <div className="soc-panel-header">
              <div>
                <div className="soc-panel-kicker">THREAT INTELLIGENCE</div>
                <h2>Classification Overview</h2>
                <p>Model classification of returned windows</p>
              </div>
            </div>

            <div className="soc-distribution-center">
              <div
                className="soc-donut"
                style={{
                  background: `conic-gradient(#ef535f 0% ${anomalyPercentage}%, #27c99a ${anomalyPercentage}% 100%)`,
                }}
              >
                <div className="soc-donut-inner">
                  <strong>{records.length}</strong>
                  <span>WINDOWS</span>
                </div>
              </div>
            </div>

            <div className="soc-distribution-legend">
              <div>
                <span><i className="legend-normal" /> Normal</span>
                <strong>{formatNumber(stats.normal.length)}</strong>
                <small>{normalPercentage.toFixed(1)}%</small>
              </div>
              <div>
                <span><i className="legend-anomaly" /> Anomaly</span>
                <strong>{formatNumber(stats.anomalies.length)}</strong>
                <small>{anomalyPercentage.toFixed(1)}%</small>
              </div>
            </div>

            <div className="soc-threshold-note">
              <span>Detection threshold</span>
              <strong>{THRESHOLD}</strong>
            </div>
          </div>
        </section>

        <section className="soc-lower-grid">
          <div className="soc-panel soc-protocol-panel">
            <div className="soc-panel-header">
              <div>
                <div className="soc-panel-kicker">NETWORK TELEMETRY</div>
                <h2>Protocol & Traffic Insights</h2>
                <p>Aggregated connection and data transfer statistics</p>
              </div>
            </div>

            <div className="soc-insight-grid">
              <div className="soc-insight-card">
                <span>TCP CONNECTIONS</span>
                <strong>{formatNumber(stats.tcp)}</strong>
                <small>Recorded TCP traffic</small>
              </div>
              <div className="soc-insight-card">
                <span>UDP CONNECTIONS</span>
                <strong>{formatNumber(stats.udp)}</strong>
                <small>Recorded UDP traffic</small>
              </div>
              <div className="soc-insight-card">
                <span>UNIQUE SOURCES</span>
                <strong>{formatNumber(stats.sources.size)}</strong>
                <small>Source IP addresses</small>
              </div>
              <div className="soc-insight-card">
                <span>DATA TRANSFERRED</span>
                <strong>{formatBytes(stats.totalBytes)}</strong>
                <small>Sent and received</small>
              </div>
            </div>
          </div>

          <div className="soc-panel soc-sources-panel">
            <div className="soc-panel-header">
              <div>
                <div className="soc-panel-kicker">SOURCE ANALYSIS</div>
                <h2>Top Network Sources</h2>
                <p>Ranked by recorded connections</p>
              </div>
            </div>

            {topSources.length === 0 ? (
              <div className="soc-chart-empty">
                {loading ? "Loading sources..." : "No source data available."}
              </div>
            ) : (
              <div className="soc-source-list">
                {topSources.map((source) => {
                  const max = Math.max(
                    1,
                    ...topSources.map((entry) => entry.connections)
                  );

                  return (
                    <div className="soc-source-item" key={source.source}>
                      <div className="soc-source-info">
                        <strong>{source.source}</strong>
                        <span>
                          {formatNumber(source.connections)} connections
                        </span>
                      </div>
                      <div className="soc-source-track">
                        <span
                          style={{
                            width: `${(source.connections / max) * 100}%`,
                          }}
                        />
                      </div>
                      {source.anomalies > 0 && (
                        <span className="soc-source-alert">
                          {source.anomalies} ALERT
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        <section className="soc-panel soc-events-panel">
          <div className="soc-panel-header soc-events-header">
            <div>
              <div className="soc-panel-kicker">SECURITY EVENT MONITOR</div>
              <h2>
                {activeView === "threats"
                  ? "Detected Threats"
                  : "Network Activity"}
              </h2>
              <p>Finalized and scored traffic windows from DynamoDB</p>
            </div>

            <div className="soc-event-controls">
              <div className="soc-search">
                <span>⌕</span>
                <input
                  type="search"
                  placeholder="Search source IP or event..."
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>

              <select
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                className="soc-filter"
              >
                <option value="ALL">All records</option>
                <option value="ANOMALY">Anomalies</option>
                <option value="NORMAL">Normal</option>
              </select>
            </div>
          </div>

          <div className="soc-table-wrap">
            <table className="soc-table">
              <thead>
                <tr>
                  <th>SOURCE IP</th>
                  <th>WINDOW START</th>
                  <th>CONNECTIONS</th>
                  <th>FAILED</th>
                  <th>ANOMALY SCORE</th>
                  <th>SEVERITY</th>
                  <th>STATUS</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((item) => {
                  const score = Number(item.anomaly_score || 0);
                  const anomaly = item.anomaly_status === "ANOMALY";
                  const severity = getSeverity(score);

                  return (
                    <tr key={getWindowKey(item)}>
                      <td className="soc-ip-cell">{getSource(item)}</td>
                      <td>{formatTime(item.window_start)}</td>
                      <td>{formatNumber(item.total_connections)}</td>
                      <td>{formatNumber(item.failed_connections)}</td>
                      <td className={anomaly ? "soc-danger-text" : ""}>
                        {score.toFixed(4)}
                      </td>
                      <td>
                        <span className={`soc-severity severity-${severity.toLowerCase()}`}>
                          {severity}
                        </span>
                      </td>
                      <td>
                        <span className={`soc-classification ${anomaly ? "anomaly" : "normal"}`}>
                          <i />
                          {item.anomaly_status || "UNSCORED"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="soc-investigate-button"
                          onClick={() => setSelectedRecord(item)}
                        >
                          Inspect ↗
                        </button>
                      </td>
                    </tr>
                  );
                })}

                {!loading && filteredRecords.length === 0 && (
                  <tr>
                    <td colSpan="8" className="soc-empty-row">
                      No matching network events found.
                    </td>
                  </tr>
                )}

                {loading && (
                  <tr>
                    <td colSpan="8" className="soc-empty-row">
                      Loading network telemetry...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="soc-table-footer">
            <span>
              DISPLAYING {filteredRecords.length} OF {records.length} RECORDS
            </span>
            <span>Auto-refresh: 30 seconds</span>
          </div>
        </section>

        <footer className="soc-footer">
          <span>NETGUARD SECURITY OPERATIONS CENTER</span>
          <span>AWS · AP-SOUTHEAST-1 · RANDOM CUT FOREST · RCF-V3</span>
        </footer>
      </main>

      {selectedRecord && (
        <div
          className="soc-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedRecord(null);
            }
          }}
        >
          <section className="soc-detail-panel" role="dialog" aria-modal="true" aria-label="Event investigation">
            <div className="soc-detail-header">
              <div>
                <div className="soc-panel-kicker">SECURITY INVESTIGATION</div>
                <h2>Event Details</h2>
              </div>
              <button
                className="soc-close-button"
                onClick={() => setSelectedRecord(null)}
                aria-label="Close event details"
              >
                ×
              </button>
            </div>

            <div className="soc-detail-source">
              <span>SOURCE IP ADDRESS</span>
              <strong>{getSource(selectedRecord)}</strong>
              <span className={`soc-classification ${selectedRecord.anomaly_status === "ANOMALY" ? "anomaly" : "normal"}`}>
                <i />
                {selectedRecord.anomaly_status || "UNSCORED"}
              </span>
            </div>

            <div className="soc-detail-score">
              <span>ANOMALY SCORE</span>
              <strong className={selectedRecord.anomaly_status === "ANOMALY" ? "soc-danger-text" : ""}>
                {Number(selectedRecord.anomaly_score || 0).toFixed(6)}
              </strong>
              <small>Detection threshold: {THRESHOLD}</small>
            </div>

            <div className="soc-detail-grid">
              <DetailItem label="Window start" value={formatTime(selectedRecord.window_start)} />
              <DetailItem label="Window key" value={selectedRecord.SK || "—"} />
              <DetailItem label="Destination IP" value={selectedRecord.destination_ip || "—"} />
              <DetailItem label="Connections" value={formatNumber(selectedRecord.total_connections)} />
              <DetailItem label="Failed connections" value={formatNumber(selectedRecord.failed_connections)} />
              <DetailItem label="Unique destination IPs" value={formatNumber(selectedRecord.unique_destination_ips)} />
              <DetailItem label="Unique destination ports" value={formatNumber(selectedRecord.unique_destination_ports)} />
              <DetailItem label="TCP connections" value={formatNumber(selectedRecord.tcp_connections)} />
              <DetailItem label="UDP connections" value={formatNumber(selectedRecord.udp_connections)} />
              <DetailItem label="Bytes sent" value={formatBytes(selectedRecord.bytes_sent)} />
              <DetailItem label="Bytes received" value={formatBytes(selectedRecord.bytes_received)} />
              <DetailItem label="Model version" value={selectedRecord.model_version || "—"} />
            </div>

            <div className="soc-detail-footer">
              <span>Record key</span>
              <code>{getWindowKey(selectedRecord)}</code>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, detail, icon, accent }) {
  return (
    <div className={`soc-metric-card accent-${accent}`}>
      <div className="soc-metric-top">
        <span>{label}</span>
        <div className="soc-metric-icon">{icon}</div>
      </div>
      <strong className="soc-metric-value">{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="soc-detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
