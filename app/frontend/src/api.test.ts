import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { api } from './api'

const nameSchema = z.object({ name: z.string() })

afterEach(() => {
  vi.unstubAllGlobals()
})

function respond(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api', () => {
  it('returns the parsed body on success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respond({ name: 'Ada' })))
    await expect(api(nameSchema, '/projects')).resolves.toEqual({ name: 'Ada' })
    expect(fetch).toHaveBeenCalledWith('/api/projects', expect.objectContaining({
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }))
  })

  it('uses the problem detail when the server rejects the call', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respond({ title: 'Missing', detail: 'No project has that id.' }, 404)))
    await expect(api(nameSchema, '/projects/missing')).rejects.toThrow('No project has that id.')
  })

  it('uses the status text when the error json is not a problem', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ error: true }), { status: 502, statusText: 'Bad gateway' })),
    )
    await expect(api(nameSchema, '/projects')).rejects.toThrow('Bad gateway')
  })

  it('rejects a success body that does not match the schema', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respond({ name: 4 })))
    await expect(api(nameSchema, '/projects')).rejects.toThrow('The API response did not match the expected shape.')
  })

  it('rejects an empty success body', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respond(null)))
    await expect(api(nameSchema, '/projects')).rejects.toThrow('The API response did not match the expected shape.')
  })

  it('rejects a success body that is not json', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('nope', { status: 200 })))
    await expect(api(nameSchema, '/projects')).rejects.toThrow()
  })
})
