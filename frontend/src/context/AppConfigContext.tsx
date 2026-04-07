import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { apiJson } from '../api/client'
import type { PublicConfigResponse } from '../api/types'
import { FALLBACK_VIDEO_URL } from '../lib/defaults'

type AppConfigContextValue = {
  config: PublicConfigResponse | null
  loading: boolean
  error: string | null
  appName: string
  appVersion: string
  demoMode: boolean
  defaultVideoUrl: string
}

const AppConfigContext = createContext<AppConfigContextValue | null>(null)

export function AppConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<PublicConfigResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const data = await apiJson<PublicConfigResponse>('/api/v1/config')
        if (!cancelled) {
          setConfig(data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  const value: AppConfigContextValue = {
    config,
    loading,
    error,
    appName: config?.app_name ?? 'YouTube Video Copilot',
    appVersion: config?.app_version ?? '0.1.0',
    demoMode: Boolean(config?.demo_mode),
    defaultVideoUrl: config?.demo_sample_video_url || FALLBACK_VIDEO_URL,
  }

  return <AppConfigContext.Provider value={value}>{children}</AppConfigContext.Provider>
}

export function useAppConfig() {
  const value = useContext(AppConfigContext)
  if (!value) {
    throw new Error('useAppConfig must be used inside AppConfigProvider')
  }
  return value
}
