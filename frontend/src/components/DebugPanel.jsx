function DebugPanel({ debug }) {
  if (!debug || !debug.suggestions.length) {
    return null
  }

  return (
    <section className="card debug-panel">
      <div className="panel-heading">
        <h2>Retrieval diagnostics</h2>
        <span>{debug.problems_found} issues</span>
      </div>
      {debug.dead_weight_items.length > 0 && (
        <div className="dead-weight-list">
          <p className="eyebrow">Dead weight detected</p>
          {debug.dead_weight_items.map((item) => (
            <div key={item.id} className="dead-weight-item">
              <strong>{item.label}</strong>
              <small>{item.reason}</small>
            </div>
          ))}
        </div>
      )}
      <ul className="suggestions-list">
        {debug.suggestions.map((suggestion, index) => (
          <li key={index} className="suggestion-item">
            <span className="suggestion-message">{suggestion.message}</span>
            <span className="suggestion-action">{suggestion.suggestion}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default DebugPanel