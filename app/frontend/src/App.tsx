import { useEffect, useState, type FormEvent } from 'react'
import { z } from 'zod'
import { api } from './api'
import {
  analyzeSchema,
  eventSchema,
  paperSchema,
  projectSchema,
  seedResultSchema,
  type AgentEvent,
  type Paper,
  type Project,
} from './schemas/api'
import './App.css'

const projectsSchema = z.array(projectSchema)
const papersSchema = z.array(paperSchema)
const eventsSchema = z.array(eventSchema)

export default function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [question, setQuestion] = useState('')
  const [seedText, setSeedText] = useState('')
  const [bibtex, setBibtex] = useState('')
  const [resolved, setResolved] = useState<Paper[]>([])
  const [unresolved, setUnresolved] = useState<string[]>([])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [results, setResults] = useState<Paper[]>([])
  const [reading, setReading] = useState<Paper | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function refreshProjects() {
    const rows = await api(projectsSchema, '/projects')
    setProjects(rows)
    return rows
  }

  useEffect(() => {
    refreshProjects().catch((err: unknown) => setError(message(err)))
  }, [])

  useEffect(() => {
    if (!selected || selected.status !== 'running') {
      return
    }
    const timer = window.setInterval(() => {
      void loadProject(selected.id)
    }, 2000)
    return () => window.clearInterval(timer)
  }, [selected])

  async function loadProject(id: string) {
    const project = await api(projectSchema, `/projects/${id}`)
    const trace = await api(eventsSchema, `/projects/${id}/events`)
    const ranked = await api(papersSchema, `/projects/${id}/results`)
    setSelected(project)
    setEvents(trace)
    setResults(ranked)
    setProjects((current) => current.map((item) => (item.id === project.id ? project : item)))
  }

  async function createProject(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const created = await api(projectSchema, '/projects', {
        method: 'POST',
        body: JSON.stringify({ name, research_question: question }),
      })
      setName('')
      setQuestion('')
      setResolved([])
      setUnresolved([])
      setResults([])
      setEvents([])
      await refreshProjects()
      setSelected(created)
    } catch (err: unknown) {
      setError(message(err))
    } finally {
      setBusy(false)
    }
  }

  async function submitSeeds(event: FormEvent) {
    event.preventDefault()
    if (!selected) {
      return
    }
    setError('')
    setBusy(true)
    const lines = seedText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
    const dois = lines.filter((line) => line.includes('10.'))
    const titles = lines.filter((line) => !line.includes('10.'))
    try {
      const outcome = await api(seedResultSchema, `/projects/${selected.id}/seeds`, {
        method: 'POST',
        body: JSON.stringify({ dois, titles, bibtex }),
      })
      setResolved(outcome.resolved)
      setUnresolved(outcome.unresolved)
    } catch (err: unknown) {
      setError(message(err))
    } finally {
      setBusy(false)
    }
  }

  async function analyze() {
    if (!selected) {
      return
    }
    setError('')
    setBusy(true)
    try {
      await api(analyzeSchema, `/projects/${selected.id}/analyze`, { method: 'POST' })
      await loadProject(selected.id)
    } catch (err: unknown) {
      setError(message(err))
    } finally {
      setBusy(false)
    }
  }

  async function sendFeedback(paperId: string, action: 'accept' | 'reject') {
    setError('')
    try {
      await api(paperSchema, `/papers/${paperId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({ action }),
      })
      if (selected) {
        await loadProject(selected.id)
      }
    } catch (err: unknown) {
      setError(message(err))
    }
  }

  return (
    <main>
      <header className="top">
        <p className="mark">Papertrail</p>
        <h1>From papers you trust to papers you can check.</h1>
      </header>
      {error ? <p className="error">{error}</p> : null}
      <section className="layout">
        <div>
          <h2>Projects</h2>
          <ul className="projects">
            {projects.map((project) => (
              <li key={project.id}>
                <button type="button" onClick={() => void loadProject(project.id).catch((err: unknown) => setError(message(err)))}>
                  {project.name}
                </button>
                <span>{project.status}</span>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => void createProject(event)}>
            <label>
              Name
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
            <label>
              Research question
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} required />
            </label>
            <button type="submit" disabled={busy}>Create project</button>
          </form>
        </div>
        {selected ? (
          <div>
            <h2>{selected.name}</h2>
            <p>{selected.research_question}</p>
            <p>Status: {selected.status}</p>
            <form onSubmit={(event) => void submitSeeds(event)}>
              <label>
                DOIs or titles, one per line
                <textarea value={seedText} onChange={(event) => setSeedText(event.target.value)} />
              </label>
              <label>
                BibTeX
                <textarea value={bibtex} onChange={(event) => setBibtex(event.target.value)} />
              </label>
              <button type="submit" disabled={busy}>Resolve seeds</button>
            </form>
            <SeedPreview resolved={resolved} unresolved={unresolved} onOpen={setReading} />
            <button type="button" onClick={() => void analyze()} disabled={busy}>Analyze</button>
            <h3>Trace</h3>
            <ol className="trace">
              {events.map((item) => (
                <li key={item.id}>
                  <strong>{item.step}</strong> · {item.tool}
                  <div>{item.output_summary}</div>
                </li>
              ))}
            </ol>
            <h3>Results</h3>
            {results.map((paper) => (
              <article key={paper.id} className="card">
                <header>
                  <h4>
                    <button type="button" className="title" onClick={() => setReading(paper)}>{paper.title}</button>
                  </h4>
                  <span className={`badge ${paper.badge}`}>{paper.badge}</span>
                </header>
                <p>
                  {authorNames(paper)} {paper.year ? `(${paper.year})` : ''} {paper.venue ?? ''}
                </p>
                <p>{paper.citation_count} citations{paper.rank_score != null ? ` · score ${paper.rank_score}` : ''}</p>
                {paper.connected_seeds.length > 0 ? <p>Connects to: {paper.connected_seeds.join('; ')}</p> : null}
                {paper.explanation ? <p>{paper.explanation}</p> : null}
                <p>
                  {paper.source_urls.map((url) => (
                    <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>
                  ))}
                </p>
                <details>
                  <summary>Evidence</summary>
                  <ul>
                    {paper.checks.map((check) => (
                      <li key={check.check_name}>
                        <strong>{check.check_name}</strong> ({check.outcome}): {String(check.evidence.fact ?? '')}
                        {check.evidence.source_url ? (
                          <a href={String(check.evidence.source_url)} target="_blank" rel="noreferrer"> source</a>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </details>
                <div className="actions">
                  <button type="button" onClick={() => void sendFeedback(paper.id, 'accept')}>Accept</button>
                  <button type="button" onClick={() => void sendFeedback(paper.id, 'reject')}>Reject</button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>
      {reading ? <Reader paper={reading} onClose={() => setReading(null)} /> : null}
    </main>
  )
}

function Reader({ paper, onClose }: { paper: Paper; onClose: () => void }) {
  const publisher = paper.source_urls.find((url) => url !== paper.pdf_url) ?? paper.source_urls[0]
  return (
    <aside className="reader">
      <header>
        <div>
          <p className="eyebrow">{paper.status === 'seed' ? 'Seed paper' : 'Suggested paper'}</p>
          <h2>{paper.title}</h2>
        </div>
        <button type="button" onClick={onClose}>Close</button>
      </header>
      {paper.pdf_url ? (
        <>
          <iframe title={paper.title} src={paper.pdf_url} />
          <p className="note">
            Some publishers block embedding. <a href={paper.pdf_url} target="_blank" rel="noreferrer">Open the PDF</a>
            {publisher ? <> or the <a href={publisher} target="_blank" rel="noreferrer">publisher page</a></> : null}.
          </p>
        </>
      ) : (
        <p className="note">
          No open PDF is available for this paper. The full text stays with the publisher.
          {publisher ? <a href={publisher} target="_blank" rel="noreferrer"> Open the publisher page</a> : null}
        </p>
      )}
    </aside>
  )
}

function SeedPreview({ resolved, unresolved, onOpen }: { resolved: Paper[]; unresolved: string[]; onOpen: (paper: Paper) => void }) {
  if (resolved.length === 0 && unresolved.length === 0) {
    return null
  }
  return (
    <div>
      <h3>Resolved seeds</h3>
      <ul>
        {resolved.map((paper) => (
          <li key={paper.id}>
            <button type="button" className="title" onClick={() => onOpen(paper)}>{paper.title}</button>
          </li>
        ))}
      </ul>
      {unresolved.length > 0 ? (
        <>
          <h3>Unresolved</h3>
          <ul>
            {unresolved.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  )
}

function authorNames(paper: Paper): string {
  return paper.authors
    .map((author) => (typeof author.name === 'string' ? author.name : ''))
    .filter(Boolean)
    .join(', ')
}

function message(err: unknown): string {
  return err instanceof Error ? err.message : 'Request failed'
}
