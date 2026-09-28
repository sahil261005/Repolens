function RepoInput({ analyzing, error, repoUrl, onChange, onAnalyze }) {

  function submit(event) {
    event.preventDefault()
    if (repoUrl.trim()) onAnalyze(repoUrl.trim())
  }

  return (
    <section className="card repo-input">
      <form onSubmit={submit}>
        <label htmlFor="repo-url">Public GitHub repository</label>
        <div className="input-row">
          <input
            id="repo-url"
            value={repoUrl}
            onChange={(event) => onChange(event.target.value)}
            placeholder="https://github.com/owner/repository"
          />
          <button type="submit" disabled={analyzing || !repoUrl.trim()}>
            {analyzing ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </form>
      {error && <p className="error-message">{error}</p>}
    </section>
  )
}

export default RepoInput
