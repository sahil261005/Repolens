function RepositoryBrief({ repo, stats }) {
  const nodeTypes = stats?.node_types || {}

  return (
    <section className="repository-brief">
      <div>
        <p className="eyebrow">Indexed repository</p>
        <h2>{repo}</h2>
        <p>Graph ready in {(stats?.indexing_ms / 1000).toFixed(1)}s · in-memory session</p>
      </div>
      <div className="repository-metrics">
        <span><strong>{stats?.node_count || 0}</strong> nodes</span>
        <span><strong>{stats?.edge_count || 0}</strong> relations</span>
        <span><strong>{nodeTypes.person || 0}</strong> people</span>
        <span><strong>{(nodeTypes.pull_request || 0) + (nodeTypes.issue || 0)}</strong> discussions</span>
      </div>
    </section>
  )
}

export default RepositoryBrief
