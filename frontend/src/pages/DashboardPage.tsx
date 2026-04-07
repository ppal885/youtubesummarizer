import { Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiJson } from '../api/client'
import type { StoredSummaryListItem } from '../api/types'
import { DashboardQuickActions } from '../components/dashboard/DashboardQuickActions'
import { DashboardRecentSection } from '../components/dashboard/DashboardRecentSection'
import { DashboardStatsCards } from '../components/dashboard/DashboardStatsCards'
import { DashboardSuggestedSection } from '../components/dashboard/DashboardSuggestedSection'
import { useAppConfig } from '../context/AppConfigContext'
import { mergeRecentVideos } from '../dashboard/mergeRecentVideos'
import { readRecentVideosLocal, readUsageStats } from '../dashboard/usageStorage'
import { formatNumber } from '../lib/formatters'
import workspace from '../styles/workspacePage.module.css'

export function DashboardPage() {
  const navigate = useNavigate()
  const { appName, demoMode, defaultVideoUrl, config } = useAppConfig()
  const demoSampleUrl = config?.demo_sample_video_url ?? null
  const [stats, setStats] = useState(() => readUsageStats())
  const [recentMerged, setRecentMerged] = useState(() =>
    mergeRecentVideos([], readRecentVideosLocal()),
  )
  const [recentLoading, setRecentLoading] = useState(true)

  const refreshLocal = useCallback(() => {
    setStats(readUsageStats())
  }, [])

  const loadRecent = useCallback(async () => {
    setRecentLoading(true)
    try {
      const rows = await apiJson<StoredSummaryListItem[]>('/api/v1/summaries?limit=16')
      setRecentMerged(mergeRecentVideos(rows, readRecentVideosLocal()))
    } catch {
      setRecentMerged(mergeRecentVideos([], readRecentVideosLocal()))
    } finally {
      setRecentLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshLocal()
    void loadRecent()
  }, [loadRecent, refreshLocal])

  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        refreshLocal()
        void loadRecent()
      }
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [loadRecent, refreshLocal])

  const openWorkspace = useCallback(
    (url: string, title?: string) => {
      navigate('/summarize', { state: { url, videoTitle: title } })
    },
    [navigate],
  )

  const focusPaste = useCallback(() => {
    document.getElementById('dashboard-paste-yt')?.focus()
  }, [])

  const serverRecentCount = recentMerged.filter((r) => r.source === 'api').length

  return (
    <Flex direction="column" gap="size-300">
      <View
        padding="size-300"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="blue-500"
        backgroundColor="static-blue-200"
      >
        <Grid columns={{ base: '1fr', L: '2fr 1fr' }} gap="size-300" alignItems="start">
          <Flex direction="column" gap="size-200">
            <Text UNSAFE_className={workspace.sectionLabelTight}>DASHBOARD</Text>
            <Heading level={1} margin={0}>
              {appName}
            </Heading>
            <Text UNSAFE_className={workspace.heroSubtitle}>
              Overview of activity: open the summarize workspace, monitor usage, and continue recent videos.
            </Text>
          </Flex>
          <Grid columns={{ base: 'repeat(3, 1fr)', L: '1fr' }} gap="size-150">
            <View padding="size-200" borderRadius="medium" backgroundColor="gray-50" borderWidth="thin" borderColor="gray-200">
              <Text UNSAFE_className={workspace.dashboardStatLabel}>SERVER ROWS</Text>
              <Text UNSAFE_className={workspace.dashboardStatValue}>
                {recentLoading ? '…' : formatNumber(serverRecentCount)}
              </Text>
            </View>
            <View padding="size-200" borderRadius="medium" backgroundColor="gray-50" borderWidth="thin" borderColor="gray-200">
              <Text UNSAFE_className={workspace.dashboardStatLabel}>MERGED RECENT</Text>
              <Text UNSAFE_className={workspace.dashboardStatValue}>
                {recentLoading ? '…' : formatNumber(recentMerged.length)}
              </Text>
            </View>
            <View padding="size-200" borderRadius="medium" backgroundColor="gray-50" borderWidth="thin" borderColor="gray-200">
              <Text UNSAFE_className={workspace.dashboardStatLabel}>MODE</Text>
              <Text UNSAFE_className={workspace.dashboardStatValue}>
                {demoMode ? 'Demo' : 'Live'}
              </Text>
            </View>
          </Grid>
        </Grid>
      </View>

      <DashboardStatsCards stats={stats} />

      <Grid columns={{ base: '1fr', L: '2fr 3fr' }} gap="size-300" alignItems="start">
        <DashboardQuickActions
          onOpenWorkspace={(url) => openWorkspace(url)}
          demoSampleUrl={demoSampleUrl}
          demoMode={demoMode}
          onFocusPasteField={focusPaste}
        />
        <DashboardRecentSection
          videos={recentMerged}
          loading={recentLoading}
          onOpenVideo={(url, title) => openWorkspace(url, title)}
          onQuickPaste={focusPaste}
        />
      </Grid>

      <DashboardSuggestedSection onOpenVideo={(url, title) => openWorkspace(url, title)} />

      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-75">
        <Text UNSAFE_className={workspace.tipLabel}>TIP</Text>
        <Text UNSAFE_className={workspace.tipBody}>
          Default new-session URL from config{demoMode ? ' (demo sample)' : ''}:{' '}
          <code className={workspace.codeInline}>{defaultVideoUrl}</code>
        </Text>
      </View>
    </Flex>
  )
}
