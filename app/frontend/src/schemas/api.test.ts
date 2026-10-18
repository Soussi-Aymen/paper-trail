import { describe, expect, it } from 'vitest'
import { librarySchema, paperBriefSchema, projectSchema } from './api'

const project = {
  id: 'p1',
  name: 'Vaccine',
  research_question: 'Does it work?',
  created_at: '2020-01-01T00:00:00',
  status: 'done',
  seed_count: 1,
  found_count: 0,
}

describe('projectSchema', () => {
  it('accepts a project with paper counts', () => {
    expect(projectSchema.parse(project).found_count).toBe(0)
  })

  it('rejects a project that omits the counts', () => {
    const { seed_count: _seed, found_count: _found, ...rest } = project
    expect(projectSchema.safeParse(rest).success).toBe(false)
  })
})

describe('paperBriefSchema', () => {
  it('accepts a title with no badge', () => {
    const parsed = paperBriefSchema.parse({
      id: 'a',
      title: 'A paper',
      authors: [],
      year: null,
      venue: null,
      citation_count: 0,
      doi: null,
      url: null,
      rank_score: null,
      badge: null,
    })
    expect(parsed.title).toBe('A paper')
  })

  it('rejects a brief whose citation count is missing', () => {
    expect(paperBriefSchema.safeParse({ id: 'a', title: 'A paper' }).success).toBe(false)
  })
})

describe('librarySchema', () => {
  it('accepts an empty library', () => {
    expect(librarySchema.parse({ seeds: [], results: [], found: [] })).toEqual({
      seeds: [],
      results: [],
      found: [],
    })
  })

  it('rejects a library that is only a list', () => {
    expect(librarySchema.safeParse([]).success).toBe(false)
  })
})
