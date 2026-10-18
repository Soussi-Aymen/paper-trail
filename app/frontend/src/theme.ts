import { z } from 'zod'

export const themeSchema = z.enum(['day', 'night'])

export type ThemeName = z.infer<typeof themeSchema>

const storageKey = 'papertrail-theme'

export function readTheme(stored: string | null): ThemeName {
  const parsed = themeSchema.safeParse(stored)
  return parsed.success ? parsed.data : 'day'
}

export function applyTheme(theme: ThemeName): void {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(storageKey, theme)
}

export function storedTheme(): ThemeName {
  return readTheme(localStorage.getItem(storageKey))
}
