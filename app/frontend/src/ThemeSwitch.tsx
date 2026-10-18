import { useState } from 'react'
import { applyTheme, storedTheme, type ThemeName } from './theme'

const themes: { id: ThemeName; symbol: string; label: string }[] = [
  { id: 'day', symbol: '☀', label: 'Day' },
  { id: 'night', symbol: '☾', label: 'Night' },
]

export default function ThemeSwitch() {
  const [theme, setTheme] = useState<ThemeName>(storedTheme)

  function choose(next: ThemeName) {
    applyTheme(next)
    setTheme(next)
  }

  return (
    <div className="theme-switch" role="group" aria-label="Theme">
      {themes.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={theme === item.id}
          onClick={() => choose(item.id)}
        >
          <span aria-hidden="true">{item.symbol}</span>
          <span className="sr">{item.label}</span>
        </button>
      ))}
    </div>
  )
}
