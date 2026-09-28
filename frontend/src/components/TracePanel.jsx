import { useState } from "react"

function TracePanel({ trace }) {
  const [open, setOpen] = useState(false)

  return (
    <section className="card trace-panel">
      <button className="trace-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>Retrieval trace</span><span>{open ? "Hide" : "Show"}</span>
      </button>
      {open && <pre>{JSON.stringify(trace, null, 2)}</pre>}
    </section>
  )
}
export default TracePanel

