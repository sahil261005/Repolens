function HealthReport({ health }) {
  if (!health) return null

  const { overall, density, coverage, freshness, coupling, insights } = health
  const coverageRate = (coverage?.commit_issue_coverage || 0) + (coverage?.pr_issue_coverage || 0)
  const avgCoverage = ((coverage?.commit_issue_coverage || 0) + (coverage?.pr_issue_coverage || 0)) / 2

  return (
    <section className="card health-report">
      <div className="panel-heading">
        <h2>Repository knowledge health</h2>
        <span className={`health-badge ${overall}`}>{overall ? overall.replace(/_/g, " ") : ""}</span>
      </div>
      <div className="health-metrics">
        <span><strong>{density}</strong><small>density</small></span>
        <span><strong>{Math.round(avgCoverage * 100)}%</strong><small>issue coverage</small></span>
        <span><strong>{freshness?.age_days ?? "N/A"}d</strong><small>last activity</small></span>
        <span><strong>{health.component_count}</strong><small>clusters</small></span>
      </div>
      {insights && insights.length > 0 && (
        <ul className="insights-list">
          {insights.map((insight, index) => (
            <li key={index} className={`insight-item ${insight.severity}`}>
              <strong>{insight.message}</strong>
              <small>{insight.suggestion}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default HealthReport