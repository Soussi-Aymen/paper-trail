import { useEffect, useRef, useState, type FormEvent } from 'react'
import { z } from 'zod'
import { api } from './api'
import {
  analyzeSchema,
  eventSchema,
  librarySchema,
  paperSchema,
  projectSchema,
  seedResultSchema,
  type AgentEvent,
  type Paper,
  type PaperBrief,
  type Project,
} from './schemas/api'
import './App.css'

const projectsSchema = z.array(projectSchema)
const eventsSchema = z.array(eventSchema)

export default function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [question, setQuestion] = useState('')
  const [seedText, setSeedText] = useState('')
  const [bibtex, setBibtex] = useState('')
  const [unresolved, setUnresolved] = useState<string[]>([])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [seeds, setSeeds] = useState<Paper[]>([])
  const [results, setResults] = useState<Paper[]>([])
  const [found, setFound] = useState<PaperBrief[]>([])
  const [reading, setReading] = useState<Paper | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const workRef = useRef<HTMLDivElement>(null)

  async function refreshProjects() {
    const rows = await api(projectsSchema, '/projects')
    setProjects(rows)
    return rows
  }

  useEffect(() => {
    refreshProjects().catch((err: unknown) => setError(message(err)))
  }, [])

  const selectedId = selected?.id
  useEffect(() => {
    if (!selectedId) {
      return
    }
    workRef.current?.scrollIntoView({ block: 'start' })
  }, [selectedId])

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
    const library = await api(librarySchema, `/projects/${id}/library`)
    setSelected(project)
    setEvents(trace)
    setSeeds(library.seeds)
    setResults(library.results)
    setFound(library.found)
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
      setUnresolved([])
      setSeeds([])
      setResults([])
      setFound([])
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
      setUnresolved(outcome.unresolved)
      await loadProject(selected.id)
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

  const trace = latestTrace(events)

  return (
    <main>
      <header className="bar">
        <p className="mark">Papertrail</p>
        <p className="tagline">Start from papers you trust. Keep the ones you can defend.</p>
      </header>
      {error ? <p className="error">{error}</p> : null}
      <section className="layout">
        <aside className="rail">
          <h2>Projects</h2>
          <ul className="projects">
            {projects.map((project) => (
              <li key={project.id}>
                <button
                  type="button"
                  className={selected?.id === project.id ? 'current' : ''}
                  onClick={() => void loadProject(project.id).catch((err: unknown) => setError(message(err)))}
                >
                  <span>
                    <span>{project.name}</span>
                    {project.seed_count + project.found_count > 0 ? (
                      <span className="count">
                        {project.seed_count} starting · {project.found_count} found
                      </span>
                    ) : null}
                  </span>
                  <span className={`status ${project.status}`}>{project.status}</span>
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => void createProject(event)}>
            <h2>New project</h2>
            <label>
              Name
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
            <label>
              Research question
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} required />
            </label>
            <button type="submit" className="secondary" disabled={busy}>Create</button>
          </form>
        </aside>
        {selected ? (
          <div className="work" ref={workRef}>
            <header className="project-head">
              <div>
                <h1>{selected.name}</h1>
                <p>{selected.research_question}</p>
              </div>
              <span className={`status ${selected.status}`}>{selected.status}</span>
            </header>
            <section>
              <h2>Papers you started from</h2>
              {seeds.length === 0 ? <p className="muted">Paste the papers you already trust. Their titles stay on this project.</p> : null}
              {seeds.map((paper) => (
                <article key={paper.id} className="card">
                  <h3>
                    <button type="button" className="title" onClick={() => setReading(paper)}>{paper.title}</button>
                  </h3>
                  <p className="meta">
                    {authorNames(paper)}
                    {paper.year ? ` · ${paper.year}` : ''}
                    {paper.venue ? ` · ${paper.venue}` : ''}
                    {` · ${paper.citation_count} citations`}
                  </p>
                  <div className="actions">
                    <button type="button" className="primary" onClick={() => setReading(paper)}>Open paper</button>
                    {paper.doi ? (
                      <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">DOI record</a>
                    ) : null}
                  </div>
                </article>
              ))}
            </section>
            <section>
              <h2>Papers to check</h2>
              {results.length === 0 ? <p className="muted">Resolve two or three seeds, then Analyze. You will get a short list, not a dump.</p> : null}
              {results.map((paper) => (
                <article key={paper.id} className="card">
                  <header>
                    <h3>
                      <button type="button" className="title" onClick={() => setReading(paper)}>{paper.title}</button>
                    </h3>
                    <span className={`badge ${paper.badge}`}>{paper.badge}</span>
                  </header>
                  <p className="meta">
                    {authorNames(paper)}
                    {paper.year ? ` · ${paper.year}` : ''}
                    {paper.venue ? ` · ${paper.venue}` : ''}
                    {` · ${paper.citation_count} citations`}
                  </p>
                  {paper.explanation ? <p>{paper.explanation}</p> : null}
                  {paper.connected_seeds.length > 0 ? <p className="muted">Linked to {paper.connected_seeds.join('; ')}</p> : null}
                  <div className="actions">
                    <button type="button" className="primary" onClick={() => setReading(paper)}>
                      {paper.pdf_url ? 'Read PDF' : 'Open paper'}
                    </button>
                    <button type="button" className="secondary" onClick={() => void sendFeedback(paper.id, 'accept')}>Accept</button>
                    <button type="button" className="secondary" onClick={() => void sendFeedback(paper.id, 'reject')}>Reject</button>
                  </div>
                  <details>
                    <summary>Why this badge</summary>
                    <ul>
                      {paper.checks.map((check) => (
                        <li key={check.check_name}>
                          <strong>{check.check_name}</strong> ({check.outcome}): {String(check.evidence.fact ?? '')}
                          {typeof check.evidence.source_url === 'string' && check.evidence.source_url ? (
                            <>
                              {' '}
                              <a href={check.evidence.source_url} target="_blank" rel="noreferrer">source</a>
                            </>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </details>
                  <details>
                    <summary>References ({paper.references.length})</summary>
                    <ul className="refs">
                      {paper.references.map((item) => (
                        <li key={item.url}>
                          <a href={item.url} target="_blank" rel="noreferrer">{item.title ?? item.url}</a>
                          {item.in_project ? <span className="muted"> · also in this project</span> : null}
                        </li>
                      ))}
                    </ul>
                  </details>
                  <ul className="refs">
                    {sourceLinks(paper).map((url) => (
                      <li key={url}>
                        <a href={url} target="_blank" rel="noreferrer">{linkLabel(url)}</a>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </section>
            <section className="composer">
              <h2>Seeds</h2>
              <form id="seeds" onSubmit={(event) => void submitSeeds(event)}>
                <label>
                  DOIs or titles, one per line
                  <textarea value={seedText} onChange={(event) => setSeedText(event.target.value)} placeholder="10.1056/NEJMoa2034577" />
                </label>
                <label>
                  BibTeX
                  <textarea value={bibtex} onChange={(event) => setBibtex(event.target.value)} />
                </label>
              </form>
              <Unresolved lines={unresolved} />
              <div className="action-row">
                <button type="submit" form="seeds" className="secondary" disabled={busy}>Resolve seeds</button>
                <button type="button" className="primary" onClick={() => void analyze()} disabled={busy}>Analyze</button>
              </div>
            </section>
            <details className="trace-box">
              <summary>How this run decided</summary>
              <ol className="trace">
                {trace.map((item) => (
                  <li key={item.id}>
                    <strong>{item.step}</strong> · {item.tool}
                    <div>{item.output_summary}</div>
                  </li>
                ))}
              </ol>
            </details>
            {found.length > 0 ? (
              <section>
                <h2>Also found ({found.length})</h2>
                <p className="muted">Titles retrieved for this question. Open one to confirm it is the article you expect.</p>
                <ul className="found">
                  {found.map((item) => (
                    <li key={item.id}>
                      <div>
                        {item.url ? (
                          <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
                        ) : (
                          <span>{item.title}</span>
                        )}
                        <p className="meta">{briefMeta(item)}</p>
                      </div>
                      {item.badge ? <span className={`badge ${item.badge}`}>{item.badge}</span> : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        ) : (
          <div className="work empty">
            <h1>Pick a project</h1>
            <p className="muted">Or create one with a question you actually want answered.</p>
          </div>
        )}
      </section>
      {reading ? <Reader paper={reading} onClose={() => setReading(null)} /> : null}
    </main>
  )
}

function latestTrace(events: AgentEvent[]): AgentEvent[] {
  let start = 0
  events.forEach((event, index) => {
    if (event.step === 'finish' && index < events.length - 1) {
      start = index + 1
    }
  })
  return events.slice(start)
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

function Unresolved({ lines }: { lines: string[] }) {
  if (lines.length === 0) {
    return null
  }
  return (
    <div>
      <h3>Unresolved</h3>
      <ul>
        {lines.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

function briefMeta(item: PaperBrief): string {
  const names = item.authors.slice(0, 3)
  const author = names.length === 0
    ? ''
    : item.authors.length > 3
      ? `${names.join(', ')} and ${item.authors.length - 3} more`
      : names.join(', ')
  return [author, item.year ? String(item.year) : '', item.venue ?? '', `${item.citation_count} citations`]
    .filter(Boolean)
    .join(' · ')
}

function sourceLinks(paper: Paper): string[] {
  const seen = new Set<string>()
  const urls: string[] = []
  for (const url of paper.source_urls) {
    if (seen.has(url) || url === paper.pdf_url) {
      continue
    }
    seen.add(url)
    urls.push(url)
  }
  return urls
}

function linkLabel(url: string): string {
  if (url.includes('doi.org')) {
    return 'DOI record'
  }
  if (url.includes('openalex.org')) {
    return 'OpenAlex record'
  }
  return url
}

function authorNames(paper: Paper): string {
  const names = paper.authors
    .map((author) => (typeof author.name === 'string' ? author.name : ''))
    .filter(Boolean)
  if (names.length <= 3) {
    return names.join(', ')
  }
  return `${names.slice(0, 3).join(', ')} and ${names.length - 3} more`
}

function message(err: unknown): string {
  return err instanceof Error ? err.message : 'Request failed'
}
