import { useMemo, useState } from "react"

function RunSummary({ run, title, active, onClick }) {
  const summary = run.trace.overlap_summary || {}
  return (
    <button className={`run-card ${active ? "active" : ""}`} onClick={onClick}>
      <span>{title}</span><strong>{run.query}</strong>
      <small>{run.intent} · {summary.efficiency === null || summary.efficiency === undefined ? "no overlap score" : `${Math.round(summary.efficiency * 100)}% efficiency`} · {run.latency_ms}ms</small>
    </button>
  )
}

function ExperimentLab({ runs, onOpenRun }) {
  const [baselineId, setBaselineId] = useState("")
  const [candidateId, setCandidateId] = useState("")
  const selected = useMemo(() => ({
    baseline: runs.find((run) => run.id === baselineId),
    candidate: runs.find((run) => run.id === candidateId),
  }), [runs, baselineId, candidateId])

  if (!runs.length) {
    return <section className="lab-empty"><p className="eyebrow">Experiment lab</p><h1>Compare retrieval runs.</h1><p>Analyze a repository and ask at least one question to build your local experiment history.</p></section>
  }

  return (
    <section className="experiment-lab">
      <p className="eyebrow">Experiment lab</p><h1>Compare retrieval quality, not just answers.</h1>
      <p className="lab-intro">Every query run is persisted locally. Pick two runs to inspect how wording changed retrieval efficiency, routing, and latency.</p>
      <div className="run-picker">
        <div><h2>Baseline</h2>{runs.map((run) => <RunSummary key={run.id} run={run} title="Run" active={run.id === baselineId} onClick={() => setBaselineId(run.id)} />)}</div>
        <div><h2>Candidate</h2>{runs.map((run) => <RunSummary key={run.id} run={run} title="Run" active={run.id === candidateId} onClick={() => setCandidateId(run.id)} />)}</div>
      </div>
      {selected.baseline && selected.candidate && (
        <section className="comparison-card">
          <h2>Experiment result</h2>
          <div>
            <span>Efficiency <strong>{Math.round((selected.baseline.trace.overlap_summary?.efficiency || 0) * 100)}% → {Math.round((selected.candidate.trace.overlap_summary?.efficiency || 0) * 100)}%</strong></span>
            <span>Latency <strong>{selected.baseline.latency_ms}ms → {selected.candidate.latency_ms}ms</strong></span>
            <span>Context size <strong>{selected.baseline.trace.final_results.length} → {selected.candidate.trace.final_results.length} items</strong></span>
          </div>
        </section>
      )}
      <button className="return-workbench" onClick={() => onOpenRun(runs[0])}>Open latest run in workbench →</button>
    </section>
  )
}

export default ExperimentLab
