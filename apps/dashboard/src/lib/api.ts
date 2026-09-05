import { demoSnapshot } from '../demo-data'
import type { DashboardSnapshot, EpisodeSummary, Metric, PipelineEvent, PipelineState } from '../types'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
const pipelineStates = new Set<PipelineState>([
  'queued', 'planning', 'researching', 'scripting', 'storyboarding',
  'asset_preparation', 'scene_production', 'scene_validation',
  'audio_production', 'rendering', 'final_validation', 'needs_approval',
  'approved', 'publishing', 'published', 'failed',
])
const metricTones = new Set(['neutral', 'positive', 'warning'])
const eventStatuses = new Set(['complete', 'active', 'waiting', 'warning'])

export const usesStaticSnapshot = !configuredApiBaseUrl

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isEpisodeSummary(value: unknown): value is EpisodeSummary {
  if (!isRecord(value)) return false

  return typeof value.id === 'string'
    && typeof value.title === 'string'
    && typeof value.objective === 'string'
    && typeof value.format === 'string'
    && typeof value.state === 'string'
    && pipelineStates.has(value.state as PipelineState)
    && typeof value.progress === 'number'
    && value.progress >= 0
    && value.progress <= 100
    && typeof value.sceneProgress === 'string'
    && typeof value.cost === 'string'
    && typeof value.scheduledFor === 'string'
}

function isMetric(value: unknown): value is Metric {
  if (!isRecord(value)) return false

  return typeof value.label === 'string'
    && typeof value.value === 'string'
    && typeof value.detail === 'string'
    && typeof value.tone === 'string'
    && metricTones.has(value.tone)
}

function isPipelineEvent(value: unknown): value is PipelineEvent {
  if (!isRecord(value)) return false

  return typeof value.id === 'string'
    && typeof value.time === 'string'
    && typeof value.title === 'string'
    && typeof value.detail === 'string'
    && typeof value.status === 'string'
    && eventStatuses.has(value.status)
}

function isDashboardSnapshot(value: unknown): value is DashboardSnapshot {
  if (!isRecord(value) || !isRecord(value.library)) return false

  return typeof value.generatedAt === 'string'
    && (value.mode === 'live' || value.mode === 'demo')
    && Array.isArray(value.metrics)
    && value.metrics.every(isMetric)
    && isEpisodeSummary(value.activeEpisode)
    && Array.isArray(value.upcomingEpisodes)
    && value.upcomingEpisodes.every(isEpisodeSummary)
    && Array.isArray(value.events)
    && value.events.every(isPipelineEvent)
    && typeof value.library.sources === 'number'
    && typeof value.library.reusableAssets === 'number'
    && typeof value.library.staleSources === 'number'
    && typeof value.library.missingRights === 'number'
    && typeof value.library.storage === 'string'
}

async function readSnapshot(response: Response): Promise<DashboardSnapshot> {
  const payload: unknown = await response.json()
  if (!isDashboardSnapshot(payload)) {
    throw new Error('Dashboard data does not match the expected contract')
  }
  return payload
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!configuredApiBaseUrl) {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}data/dashboard.json`, {
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      if (!response.ok) throw new Error(`Static dashboard data returned ${response.status}`)
      return await readSnapshot(response)
    } catch {
      return demoSnapshot
    }
  }

  const response = await fetch(`${configuredApiBaseUrl}/api/v1/dashboard`, {
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Dashboard API returned ${response.status}`)
  }

  return readSnapshot(response)
}

export async function advanceDemoPipeline(): Promise<DashboardSnapshot> {
  if (!configuredApiBaseUrl) {
    return demoSnapshot
  }

  const response = await fetch(`${configuredApiBaseUrl}/api/v1/demo/advance`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Pipeline command returned ${response.status}`)
  }

  return readSnapshot(response)
}
