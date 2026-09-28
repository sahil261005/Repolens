function EfficiencyBar({ summary }) {
  // shows what fraction of retrieved items actually showed up in the answer
  // the stacked bar breaks it down by confidence tier
  const hasAnswer = summary?.efficiency !== null && summary?.efficiency !== undefined
  const percent = hasAnswer ? Math.round(summary.efficiency * 100) : 0
  const { high, medium, low, unknown, total_tokens, used_tokens, dead_weight_tokens, wasted_token_pct } = summary || {}
  const total = high !== undefined ? high + medium + low + unknown : 0

  return (
    <section className="card efficiency-panel">
      <p className="eyebrow">Retrieval efficiency</p>
      <strong>{hasAnswer ? `${summary.used} of ${summary.retrieved}` : "Not available"}</strong>
      <p>{hasAnswer ? "retrieved items appear in the answer." : "An answer was not generated for comparison."}</p>
      <div className="efficiency-track" aria-label={`${percent}% retrieval efficiency`}>
        <span className="high" style={{ width: `${total > 0 ? Math.round((high / total) * 100) : 0}%` }} title={`High confidence: ${high || 0}`} />
        <span className="medium" style={{ width: `${total > 0 ? Math.round((medium / total) * 100) : 0}%` }} title={`Medium confidence: ${medium || 0}`} />
        <span className="low" style={{ width: `${total > 0 ? Math.round((low / total) * 100) : 0}%` }} title={`Low confidence / dead weight: ${low || 0}`} />
      </div>

      {hasAnswer && total_tokens > 0 && (
        <div className="token-telemetry">
          <span className="wasted-badge">
            ~{dead_weight_tokens?.toLocaleString() || 0} dead-weight tokens ({wasted_token_pct || 0}% context bloat)
          </span>
          <small className="muted-text">
            Prompt context: ~{total_tokens?.toLocaleString() || 0} tokens (~{used_tokens?.toLocaleString() || 0} active)
          </small>
        </div>
      )}

      <small className="disclaimer">Used means lexical overlap, not causal attribution.</small>
    </section>
  )
}

export default EfficiencyBar
