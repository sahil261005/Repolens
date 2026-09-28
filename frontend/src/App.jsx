import { useEffect, useMemo, useState } from "react"
import api from "./api"
import AnswerPanel from "./components/AnswerPanel"
import DebugPanel from "./components/DebugPanel"
import EfficiencyBar from "./components/EfficiencyBar"
import ExperimentLab from "./components/ExperimentLab"
import GraphView from "./components/GraphView"
import HealthReport from "./components/HealthReport"
import InsightsPanel from "./components/InsightsPanel"
import QueryBox from "./components/QueryBox"
import RepoInput from "./components/RepoInput"
import RepositoryBrief from "./components/RepositoryBrief"
import ResultsList from "./components/ResultsList"
import TracePanel from "./components/TracePanel"
import WeightSlider from "./components/WeightSlider"

function App() {
  const [repo, setRepo] = useState("")
  const [repoUrl, setRepoUrl] = useState("")
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState("")
  const [answer, setAnswer] = useState("")
  const [trace, setTrace] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [runHistory, setRunHistory] = useState([])
  const [activeView, setActiveView] = useState("workbench")

  const defaultVectorWeight = trace?.weights?.vector ?? 0.8
  const [customVectorWeight, setCustomVectorWeight] = useState(0.8)
  const [isUserTuned, setIsUserTuned] = useState(false)

  // sync slider to the trace's weight unless the user manually dragged it
  useEffect(() => {
    if (!isUserTuned && trace?.weights?.vector !== undefined) {
      setCustomVectorWeight(trace.weights.vector)
    }
  }, [trace, isUserTuned])

  function handleWeightChange(newWeight) {
    setIsUserTuned(true)
    setCustomVectorWeight(newWeight)
  }

  function handleResetWeight() {
    setIsUserTuned(false)
    if (trace?.weights?.vector !== undefined) {
      setCustomVectorWeight(trace.weights.vector)
    } else {
      setCustomVectorWeight(0.8)
    }
  }

  // this is the "what-if" reranking - recomputes scores client-side
  // without hitting the server, so the slider feels instant
  const displayedResults = useMemo(() => {
    if (!trace?.final_results) return []
    const vW = customVectorWeight
    const gW = 1 - vW
    return trace.final_results
      .map((item) => {
        const recomputed = (vW * item.vector_score + gW * item.graph_score) * (item.recency_factor ?? 1.0)
        return {
          ...item,
          final_score: Number(recomputed.toFixed(4)),
        }
      })
      .sort((a, b) => b.final_score - a.final_score)
  }, [trace, customVectorWeight])

  const selectedItem = useMemo(
    () => displayedResults.find((r) => r.id === selectedId) || displayedResults[0] || null,
    [displayedResults, selectedId]
  )

  async function loadHistory(currentRepo) {
    try {
      const response = await api.get("/api/history", { params: currentRepo ? { repo: currentRepo } : {} })
      setRunHistory(response.data.runs)
    } catch {
      setRunHistory([])
    }
  }

  async function analyze(targetUrl) {
    setAnalyzing(true)
    setError("")
    setAnswer("")
    setTrace(null)
    setSelectedId(null)
    setHealth(null)
    setIsUserTuned(false)

    try {
      const response = await api.post("/api/analyze", { repo_url: targetUrl })
      setRepo(response.data.repo)
      setStats(response.data.stats)
      setHealth(response.data.health || null)
      loadHistory(response.data.repo)
    } catch (requestError) {
      setRepo("")
      setStats(null)
      setHealth(null)
      setError(requestError.response?.data?.detail || "Could not analyze this repository.")
    } finally {
      setAnalyzing(false)
    }
  }

  async function ask(query) {
    setAsking(true)
    setError("")

    try {
      const payload = {
        repo,
        query,
        vector_weight: isUserTuned ? customVectorWeight : null,
      }
      const response = await api.post("/api/query", payload)
      setAnswer(response.data.answer)
      setTrace(response.data.trace)
      const firstId = response.data.trace.final_results[0]?.id || null
      setSelectedId(firstId)
      loadHistory(repo)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not answer this question.")
    } finally {
      setAsking(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">R</span>
          <span>RepoLens</span>
        </div>
        <nav aria-label="Primary navigation">
          <button className={activeView === "workbench" ? "nav-active" : ""} onClick={() => setActiveView("workbench")}>
            Workbench
          </button>
          <button className={activeView === "lab" ? "nav-active" : ""} onClick={() => setActiveView("lab")}>
            Experiment lab
          </button>
        </nav>
        <span className="beta-label">PUBLIC REPOS · BETA</span>
      </header>

      <div className="page-shell">
        {activeView === "lab" ? (
          <ExperimentLab
            runs={runHistory}
            onOpenRun={(run) => {
              setAnswer(run.answer)
              setTrace(run.trace)
              setSelectedId(run.trace.final_results[0]?.id || null)
              setActiveView("workbench")
            }}
          />
        ) : (
          <>
            <header className="hero">
              <p className="eyebrow">GitHub retrieval intelligence</p>
              <h1>
                Inspect the evidence<br />
                <em>behind every answer.</em>
              </h1>
              <p>
                Analyze a public repository, trace hybrid retrieval, and measure whether the evidence actually made it into the answer.
              </p>
            </header>

            <section className="demo-row">
              <span>Try a public demo</span>
              <button onClick={() => setRepoUrl("fastapi/fastapi")}>FastAPI</button>
              <button onClick={() => setRepoUrl("pallets/flask")}>Flask</button>
              <button onClick={() => setRepoUrl("psf/requests")}>Requests</button>
            </section>
            <RepoInput
              analyzing={analyzing}
              error={error}
              repoUrl={repoUrl}
              onChange={setRepoUrl}
              onAnalyze={analyze}
            />
            {repo && <RepositoryBrief repo={repo} stats={stats} />}
            {health && <HealthReport health={health} />}
            <QueryBox disabled={!repo} asking={asking} onAsk={ask} />

            {trace && (
              <>
                <section className="answer-grid">
                  <AnswerPanel answer={answer} trace={trace} selectedItem={selectedItem} />
                  <EfficiencyBar summary={trace.overlap_summary} />
                </section>

                <WeightSlider
                  vectorWeight={customVectorWeight}
                  defaultWeight={defaultVectorWeight}
                  isUserTuned={isUserTuned}
                  onChange={handleWeightChange}
                  onReset={handleResetWeight}
                />

                <DebugPanel debug={trace.debug} />
                <InsightsPanel trace={trace} results={displayedResults} />

                <section className="workspace-grid">
                  <ResultsList results={displayedResults} selectedId={selectedId} onSelect={setSelectedId} />
                  <GraphView
                    repo={repo}
                    selectedId={selectedId}
                    results={displayedResults}
                    graphHits={trace.graph_hits}
                    onSelectNode={setSelectedId}
                  />
                </section>
                <TracePanel trace={trace} />
              </>
            )}
          </>
        )}
      </div>
    </main>
  )
}

export default App
