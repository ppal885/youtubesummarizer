import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'theme'

type Theme = 'light' | 'dark'

function readInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  try {
    const s = localStorage.getItem(STORAGE_KEY)
    if (s === 'dark' || s === 'light') return s
  } catch {
    /* ignore */
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

type ThemeContextValue = {
  theme: Theme
  /** True when `theme === 'dark'` */
  isDark: boolean
  setTheme: (next: Theme) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readInitialTheme)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* ignore quota / private mode */
    }
  }, [theme])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeState((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  const value = useMemo(
    () => ({
      theme,
      isDark: theme === 'dark',
      setTheme,
      toggleTheme,
    }),
    [theme, setTheme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return ctx
}
