export type PipelineState =
  | 'queued'
  | 'planning'
  | 'researching'
  | 'scripting'
  | 'script_validation'
  | 'storyboarding'
  | 'asset_preparation'
  | 'scene_production'
  | 'scene_validation'
  | 'audio_production'
  | 'rendering'
  | 'final_validation'
  | 'needs_approval'
  | 'approved'
  | 'publishing'
  | 'published'
  | 'failed'
  | 'paused'
  | 'cancelled'

export interface Metric {
  label: string
  value: string
  detail: string
  tone: 'neutral' | 'positive' | 'warning'
}

export interface PipelineEvent {
  id: string
  time: string
  title: string
  detail: string
  status: 'complete' | 'active' | 'waiting' | 'warning'
}

export interface EpisodeSummary {
  id: string
  title: string
  objective: string
  format: string
  state: PipelineState
  progress: number
  sceneProgress: string
  cost: string
  scheduledFor: string
}

export interface LibrarySummary {
  sources: number
  reusableAssets: number
  staleSources: number
  missingRights: number
  storage: string
}

export interface DashboardSnapshot {
  generatedAt: string
  mode: 'live' | 'demo'
  metrics: Metric[]
  activeEpisode: EpisodeSummary
  upcomingEpisodes: EpisodeSummary[]
  events: PipelineEvent[]
  library: LibrarySummary
}
