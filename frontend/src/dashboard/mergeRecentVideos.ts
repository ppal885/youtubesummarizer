import type { StoredSummaryListItem } from '../api/types'
import type { RecentVideoLocal } from './usageStorage'

export type DashboardRecentVideo = {
  videoId: string
  url: string
  title: string
  processedAt: string
  source: 'api' | 'local'
}

function parseTime(iso: string): number {
  const t = Date.parse(iso)
  return Number.isNaN(t) ? 0 : t
}

/** Merge API summaries with locally tracked sessions; dedupe by video id (newest wins). */
export function mergeRecentVideos(
  apiRows: StoredSummaryListItem[],
  local: RecentVideoLocal[],
): DashboardRecentVideo[] {
  const map = new Map<string, DashboardRecentVideo>()

  for (const row of apiRows) {
    const processedAt = row.created_at
    map.set(row.video_id, {
      videoId: row.video_id,
      url: row.source_url,
      title: row.title || 'Untitled video',
      processedAt,
      source: 'api',
    })
  }

  for (const row of local) {
    const existing = map.get(row.videoId)
    const localTime = parseTime(row.processedAt)
    const apiTime = existing ? parseTime(existing.processedAt) : -1
    if (!existing || localTime >= apiTime) {
      map.set(row.videoId, {
        videoId: row.videoId,
        url: row.url,
        title: row.title,
        processedAt: row.processedAt,
        source: 'local',
      })
    }
  }

  return [...map.values()].sort((a, b) => parseTime(b.processedAt) - parseTime(a.processedAt))
}
