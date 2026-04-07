import { Provider, defaultTheme } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'
import { useNavigate, type To } from 'react-router-dom'
import { ThemeProvider, useTheme } from '../context/ThemeContext'

function SpectrumProviderBridge({ children }: { children: ReactNode }) {
  const { theme } = useTheme()
  const navigate = useNavigate()

  return (
    <Provider
      theme={defaultTheme}
      colorScheme={theme === 'dark' ? 'dark' : 'light'}
      locale="en-US"
      router={{
        navigate: (path, options) => {
          const to = typeof path === 'string' ? path : (path as To)
          const replace =
            options !== undefined &&
            typeof options === 'object' &&
            options !== null &&
            'replace' in options &&
            Boolean((options as { replace?: boolean }).replace)
          navigate(to, { replace })
        },
      }}
    >
      {children}
    </Provider>
  )
}

/** Compose theme state + Adobe React Spectrum `Provider` (must sit under `BrowserRouter`). */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <SpectrumProviderBridge>{children}</SpectrumProviderBridge>
    </ThemeProvider>
  )
}
