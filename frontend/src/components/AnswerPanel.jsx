function renderAnswerText(answer, selectedItem) {
  if (!answer) return null
  const sharedTokens = selectedItem?.shared_tokens
  if (!sharedTokens || sharedTokens.length === 0) {
    return <p className="answer-text">{answer}</p>
  }
  const tokenSet = new Set(sharedTokens.map((t) => t.toLowerCase()))
  // split on whitespace AND punctuation but keep them as separators
  // so the highlighted output still reads normally
  const words = answer.split(/(\s+|[^\w\s]+)/)
  return (
    <p className="answer-text">
      {words.map((chunk, index) => {
        const cleaned = chunk.toLowerCase().replace(/[^a-z0-9]/g, "")
        if (cleaned && tokenSet.has(cleaned)) {
          return (
            <mark
              key={index}
              className="token-match"
              title={`Matched token in "${selectedItem.label}"`}
            >
              {chunk}
            </mark>
          )
        }
        return chunk
      })}
    </p>
  )
}

function AnswerPanel({ answer, trace, selectedItem }) {
  const weights = trace?.weights || {}
  const sharedTokens = selectedItem?.shared_tokens || []

  return (
    <section className="card answer-panel">
      <div className="panel-heading">
        <h2>Answer</h2>
        <span className={`intent-badge ${trace?.intent || "semantic"}`}>
          {trace?.intent || "semantic"}
        </span>
      </div>
      {renderAnswerText(answer, selectedItem)}
      {selectedItem && (
        <div className="overlap-hint">
          {sharedTokens.length > 0 ? (
            <span>
              Shared with selected item:{" "}
              {sharedTokens.map((tok) => (
                <code key={tok} className="token-tag">{tok}</code>
              ))}
            </span>
          ) : (
            <span className="muted-text">No direct lexical overlap with selected item.</span>
          )}
        </div>
      )}
      <p className="muted-text">
        Fusion: {Math.round((weights.vector || 0) * 100)}% vector ·{" "}
        {Math.round((weights.graph || 0) * 100)}% graph
      </p>
    </section>
  )
}

export default AnswerPanel
