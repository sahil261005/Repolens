import { useState } from "react"

const SUGGESTED_QUERIES = [
  { label: "Who fixed the login bug?", query: "Who fixed the login bug?" },
  { label: "How does middleware work?", query: "How does middleware and routing work?" },
  { label: "Which issues were resolved?", query: "Which issues are resolved by recent PRs?" },
]

function QueryBox({ disabled, asking, onAsk }) {
  const [query, setQuery] = useState("")

  function submit(event) {
    event.preventDefault()
    if (query.trim()) onAsk(query.trim())
  }

  function handleSuggest(suggested) {
    setQuery(suggested)
    if (!disabled && !asking) {
      onAsk(suggested)
    }
  }

  return (
    <section className="card query-box">
      <form onSubmit={submit}>
        <label htmlFor="query">Ask about the repository</label>
        <div className="input-row">
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Who fixed the login bug? or How does caching work?"
            disabled={disabled}
          />
          <button type="submit" disabled={disabled || asking || !query.trim()}>
            {asking ? "Searching…" : "Ask"}
          </button>
        </div>
      </form>

      <div className="sample-queries">
        <span>Quick queries:</span>
        {SUGGESTED_QUERIES.map((item) => (
          <button
            key={item.label}
            type="button"
            disabled={disabled || asking}
            onClick={() => handleSuggest(item.query)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  )
}

export default QueryBox
