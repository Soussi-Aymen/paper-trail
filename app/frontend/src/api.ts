import type { ZodType } from 'zod'
import { problemSchema } from './schemas/api'

export async function api<T>(schema: ZodType<T>, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  const body: unknown = await response.json()
  if (!response.ok) {
    const problem = problemSchema.safeParse(body)
    const detail = problem.success ? problem.data.detail : response.statusText
    throw new Error(detail)
  }
  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    throw new Error('The API response did not match the expected shape.')
  }
  return parsed.data
}
