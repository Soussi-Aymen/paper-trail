import { z } from 'zod'

export const projectSchema = z.object({
  id: z.string(),
  name: z.string(),
  research_question: z.string(),
  created_at: z.string(),
  status: z.string(),
})

export const checkSchema = z.object({
  check_name: z.string(),
  outcome: z.string(),
  evidence: z.record(z.string(), z.unknown()),
})

export const paperSchema = z.object({
  id: z.string(),
  title: z.string(),
  authors: z.array(z.record(z.string(), z.unknown())),
  year: z.number().nullable(),
  venue: z.string().nullable(),
  citation_count: z.number(),
  doi: z.string().nullable(),
  openalex_id: z.string().nullable(),
  source_urls: z.array(z.string()),
  pdf_url: z.string().nullable(),
  status: z.string(),
  rank_score: z.number().nullable(),
  score_breakdown: z.record(z.string(), z.number()).nullable(),
  badge: z.string(),
  checks: z.array(checkSchema),
  explanation: z.string().nullable(),
  explanation_grounded: z.boolean().nullable(),
  connected_seeds: z.array(z.string()),
  discovery_paths: z.array(z.unknown()),
})

export const seedResultSchema = z.object({
  resolved: z.array(paperSchema),
  unresolved: z.array(z.string()),
})

export const eventSchema = z.object({
  id: z.string(),
  step: z.string(),
  tool: z.string(),
  input: z.record(z.string(), z.unknown()),
  output_summary: z.string(),
  created_at: z.string(),
})

export const analyzeSchema = z.object({
  project_id: z.string(),
  status: z.string(),
})

export const problemSchema = z.object({
  title: z.string(),
  detail: z.string(),
})

export type Project = z.infer<typeof projectSchema>
export type Paper = z.infer<typeof paperSchema>
export type AgentEvent = z.infer<typeof eventSchema>
