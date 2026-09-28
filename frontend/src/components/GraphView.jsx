import { useEffect, useMemo, useState } from "react"
import ReactFlow, { Background, Controls } from "reactflow"
import "reactflow/dist/style.css"
import api from "../api"

function GraphView({ repo, selectedId, results, graphHits, onSelectNode }) {
  const [graph, setGraph] = useState({ nodes: [], edges: [] })

  // fetch the subgraph around the selected node whenever it changes
  useEffect(() => {
    if (!repo || !selectedId) return

    api.post("/api/subgraph", { repo, node_ids: [selectedId] })
      .then((response) => setGraph(response.data))
      .catch(() => setGraph({ nodes: [], edges: [] }))
  }, [repo, selectedId])

  const selectedPath = useMemo(
    () => graphHits?.find((hit) => hit.id === selectedId)?.path || [selectedId],
    [graphHits, selectedId]
  )
  const usedById = useMemo(
    () => Object.fromEntries(results.map((item) => [item.id, item.used])),
    [results]
  )

  // figure out which edges are part of the traversal path so we can animate them
  const pathEdges = new Set(selectedPath.slice(1).map((nodeId, index) => {
    const previous = selectedPath[index]
    return [previous, nodeId].sort().join("-")
  }))

  // radial layout - put the selected node in the center and arrange
  // neighbours in a circle around it. looks much better than the
  // default force layout for small subgraphs
  const nodes = useMemo(() => {
    const otherNodes = graph.nodes.filter((n) => n.id !== selectedId)
    const neighborCount = otherNodes.length
    const radius = neighborCount > 8 ? 180 : 140
    const centerX = 260
    const centerY = 190

    let otherIndex = 0
    return graph.nodes.map((node) => {
      let position
      if (node.id === selectedId) {
        position = { x: centerX, y: centerY }
      } else {
        const theta = (2 * Math.PI * otherIndex) / (neighborCount || 1)
        position = {
          x: Math.round(centerX + radius * Math.cos(theta)),
          y: Math.round(centerY + radius * Math.sin(theta)),
        }
        otherIndex++
      }

      return {
        ...node,
        position,
        className: `graph-node ${node.data.type} ${usedById[node.id] === false ? "dimmed" : ""} ${node.id === selectedId ? "active" : ""}`,
      }
    })
  }, [graph.nodes, selectedId, usedById])

  const edges = graph.edges.map((edge) => ({
    ...edge,
    animated: pathEdges.has([edge.source, edge.target].sort().join("-")),
    className: pathEdges.has([edge.source, edge.target].sort().join("-")) ? "path-edge" : "",
  }))

  return (
    <section className="card graph-panel">
      <div className="panel-heading">
        <h2>Traversal graph</h2>
        <span>Radial layout · Click node to inspect</span>
      </div>
      <div className="graph-canvas">
        {nodes.length ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            nodesDraggable={true}
            nodesConnectable={false}
            onNodeClick={(_, node) => onSelectNode?.(node.id)}
          >
            <Background gap={18} size={1} />
            <Controls showInteractive={true} />
          </ReactFlow>
        ) : (
          <p className="empty-graph">Select a retrieved item to inspect its graph connections.</p>
        )}
      </div>
    </section>
  )
}

export default GraphView
