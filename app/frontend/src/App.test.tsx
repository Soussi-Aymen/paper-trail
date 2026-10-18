import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

beforeEach(() => {
  localStorage.clear()
  document.documentElement.dataset.theme = 'day'
})

function project(overrides: Record<string, unknown> = {}) {
  return {
    id: 'p1',
    name: 'Vaccine evidence',
    research_question: 'Does it work?',
    created_at: '2020-01-01T00:00:00',
    status: 'done',
    seed_count: 1,
    found_count: 1,
    ...overrides,
  }
}

function paper(overrides: Record<string, unknown> = {}) {
  return {
    id: 'paper-1',
    title: 'Safety of the trial vaccine',
    authors: [{ name: 'Ada Lovelace' }],
    year: 2020,
    venue: 'The Lancet',
    citation_count: 12,
    doi: '10.1000/trial',
    openalex_id: 'W1',
    source_urls: ['https://doi.org/10.1000/trial'],
    pdf_url: null,
    status: 'seed',
    rank_score: null,
    score_breakdown: null,
    badge: 'yellow',
    checks: [],
    explanation: null,
    explanation_grounded: null,
    connected_seeds: [],
    references: [],
    discovery_paths: [],
    ...overrides,
  }
}

function brief(overrides: Record<string, unknown> = {}) {
  return {
    id: 'found-1',
    title: 'A related cohort study',
    authors: ['Grace Hopper'],
    year: 2021,
    venue: 'BMJ',
    citation_count: 3,
    doi: '10.1000/cohort',
    url: 'https://doi.org/10.1000/cohort',
    rank_score: 0.2,
    badge: null,
    ...overrides,
  }
}

function stubApi(routes: Record<string, unknown>, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const path = String(input).replace(/^\/api/, '')
      if (init?.method === 'POST' && path === '/projects') {
        return json({ ...project({ id: 'p2', name: 'New question', status: 'draft', seed_count: 0, found_count: 0 }), ...JSON.parse(String(init.body)) , id: 'p2', created_at: '2020-01-02T00:00:00', status: 'draft', seed_count: 0, found_count: 0 })
      }
      const body = routes[path]
      if (body === undefined) {
        return json({ title: 'Missing', detail: 'No route in the test.' }, 404)
      }
      return json(body, status)
    }),
  )
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('theme control', () => {
  it('switches to night and back to day', async () => {
    stubApi({ '/projects': [] })
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Pick a project' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Night' }))
    expect(document.documentElement.dataset.theme).toBe('night')
    expect(localStorage.getItem('papertrail-theme')).toBe('night')
    fireEvent.click(screen.getByRole('button', { name: 'Day' }))
    expect(document.documentElement.dataset.theme).toBe('day')
    expect(localStorage.getItem('papertrail-theme')).toBe('day')
  })
})

describe('project screen', () => {
  it('shows the starting paper and the other found title', async () => {
    stubApi({
      '/projects': [project()],
      '/projects/p1': project(),
      '/projects/p1/events': [],
      '/projects/p1/library': {
        seeds: [paper()],
        results: [paper({ id: 'paper-2', title: 'Efficacy against the variant', status: 'verified', badge: 'green' })],
        found: [brief()],
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /Vaccine evidence/ }))
    expect(await screen.findByRole('heading', { name: 'Papers you started from' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Safety of the trial vaccine' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Efficacy against the variant' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'A related cohort study' }).getAttribute('href')).toBe('https://doi.org/10.1000/cohort')
  })

  it('shows the server detail when loading projects fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ title: 'Down', detail: 'Postgres is not reachable.' }, 503)))
    render(<App />)
    expect(await screen.findByText('Postgres is not reachable.')).toBeTruthy()
  })

  it('shows a shape error when the project list is not the expected json', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ projects: [] })))
    render(<App />)
    expect(await screen.findByText('The API response did not match the expected shape.')).toBeTruthy()
  })

  it('keeps the empty copy when a project has no papers yet', async () => {
    const empty = project({ seed_count: 0, found_count: 0, status: 'draft' })
    stubApi({
      '/projects': [empty],
      '/projects/p1': empty,
      '/projects/p1/events': [],
      '/projects/p1/library': { seeds: [], results: [], found: [] },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /Vaccine evidence/ }))
    expect(await screen.findByText('Paste the papers you already trust. Their titles stay on this project.')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: /Also found/ })).toBeNull()
  })

  it('creates a project from the form', async () => {
    stubApi({ '/projects': [] })
    render(<App />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'New question' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Research question' }), { target: { value: 'Why?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByRole('heading', { name: 'New question' })).toBeTruthy()
  })

  it('shows the detail when creating a project is rejected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: RequestInfo, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return json({ title: 'Invalid', detail: 'Name is required.' }, 422)
        }
        return json([])
      }),
    )
    render(<App />)
    fireEvent.change(await screen.findByRole('textbox', { name: 'Name' }), { target: { value: 'New question' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Research question' }), { target: { value: 'Why?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByText('Name is required.')).toBeTruthy()
  })
})
