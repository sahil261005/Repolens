function Score({ label, value }) {
  return <span><small>{label}</small>{Number(value).toFixed(3)}</span>
}

function ResultsList({ results, selectedId, onSelect }) {
  return (
    <section className="card results-list">
      <div className="panel-heading">
        <h2>Retrieved items</h2>
        <span>{results.length} items ranked</span>
      </div>
      {results.map((item, index) => {
        const isSelected = selectedId === item.id
        return (
          <button
            className={`result-row ${isSelected ? "selected" : ""} ${item.used === false ? "unused" : ""}`}
            key={item.id}
            onClick={() => onSelect(item.id)}
          >
            <div className="result-title">
              <span className="rank">{index + 1}</span>
              <span>{item.label}</span>
            </div>
            <div className="result-meta">
              <span className="type-badge">{item.type.replace("_", " ")}</span>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(event) => event.stopPropagation()}
                >
                  GitHub ↗
                </a>
              )}
              {item.age_days !== null && item.age_days !== undefined && <span>{item.age_days}d old</span>}
              {item.token_estimate !== undefined && <span>~{item.token_estimate} tokens</span>}
              {item.used !== null && item.used !== undefined && (
                <span className={`usage ${item.used ? "used" : "not-used"}`}>
                  {item.used ? "used" : "not used"}
                </span>
              )}
              {item.confidence !== null && item.confidence !== undefined && (
                <span className={`confidence ${item.confidence}`}>{item.confidence}</span>
              )}
            </div>

            {isSelected && item.shared_tokens && item.shared_tokens.length > 0 && (
              <div className="matched-tokens-row">
                <small>Shared tokens in answer:</small>
                <div className="token-tags">
                  {item.shared_tokens.map((tok) => (
                    <code key={tok} className="token-tag">{tok}</code>
                  ))}
                </div>
              </div>
            )}

            <div className="scores">
              <Score label="Vector" value={item.vector_score} />
              <Score label="Graph" value={item.graph_score} />
              <Score label="Final" value={item.final_score} />
            </div>
          </button>
        )
      })}
    </section>
  )
}

export default ResultsList
