function Insight({ label, value, detail }) {
  return <div className="insight"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
}

function InsightsPanel({ trace, results }) {
  const funnel = trace.funnel || {}
  const summary = trace.overlap_summary || {}
  const unused = Math.max(0, (summary.retrieved || 0) - (summary.used || 0))
  const graphFirst = results.filter((result) => result.graph_score > result.vector_score).length

  return (
    <section className="insights-panel">
      <div className="insights-header">
        <div><p className="eyebrow">Retrieval investigation</p><h2>Why this answer looks the way it does</h2></div>
        <span>{trace.timing?.total_ms || 0} ms total</span>
      </div>
      <div className="funnel-row" aria-label="Retrieval funnel">
        <span>{funnel.repository_nodes || 0}<small>repository nodes</small></span><i>→</i>
        <span>{funnel.vector_candidates || 0}<small>vector candidates</small></span><i>→</i>
        <span>{funnel.graph_candidates || 0}<small>graph-expanded</small></span><i>→</i>
        <span>{funnel.final_context || 0}<small>final context</small></span>
      </div>
      <div className="insight-grid">
        <Insight label="Dead-weight context" value={`${unused} items`} detail="Retrieved but did not lexically appear in the answer." />
        <Insight label="Graph-led evidence" value={`${graphFirst}/${results.length}`} detail="Final results where path strength outweighed semantic similarity." />
        <Insight label="Routing decision" value={trace.intent} detail={`Classified by ${trace.intent_source}.`} />
      </div>
    </section>
  )
}

export default InsightsPanel
