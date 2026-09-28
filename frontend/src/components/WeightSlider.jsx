function WeightSlider({ vectorWeight, defaultWeight, isUserTuned, onChange, onReset }) {
  // when the user drags the slider, we "lock" their weight choice
  // and use it for both instant reranking AND the next server query
  const percentVector = Math.round(vectorWeight * 100)
  const percentGraph = 100 - percentVector
  const isCustom = isUserTuned || Math.abs(vectorWeight - defaultWeight) > 0.01

  return (
    <div className="card weight-slider-card">
      <div className="slider-header">
        <div>
          <span className="eyebrow">What-If Fusion Re-ranker</span>
          <h3>Tune Retrieval Weights</h3>
        </div>
        <div className="slider-actions">
          {isCustom ? (
            <span className="status-badge custom" title="This weight split will be used for live re-ranking AND subsequent queries">
              Locked ({percentVector}% V / {percentGraph}% G)
            </span>
          ) : (
            <span className="status-badge auto" title="Weights are automatically classified per query">
              Auto (Intent-classified)
            </span>
          )}
          {isCustom && (
            <button className="reset-button" onClick={onReset} title="Reset to classified intent weights">
              Reset to Auto
            </button>
          )}
        </div>
      </div>
      <div className="slider-controls">
        <span className="slider-label vector">Vector: {percentVector}%</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={vectorWeight}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="fusion-range"
        />
        <span className="slider-label graph">Graph: {percentGraph}%</span>
      </div>
      <p className="slider-hint">
        {isCustom
          ? "Custom weights locked: Results are re-ranked now and future 'Ask' queries will use this split."
          : "Drag to simulate what-if splits or prioritize graph traversal over semantic text search."}
      </p>
    </div>
  )
}

export default WeightSlider
