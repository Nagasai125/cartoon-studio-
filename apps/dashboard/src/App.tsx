import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Archive,
  ArrowRight,
  BookOpen,
  Bot,
  CalendarDays,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Database,
  Film,
  Gauge,
  Library,
  Menu,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react'
import { useState } from 'react'

import { advanceDemoPipeline, getDashboardSnapshot, usesStaticSnapshot } from './lib/api'
import { formatGeneratedAt, formatState } from './lib/format'
import type { DashboardSnapshot, PipelineEvent } from './types'

const navigation = [
  { label: 'Overview', icon: Gauge, active: true },
  { label: 'Productions', icon: Film },
  { label: 'Review', icon: ShieldCheck, count: 1 },
  { label: 'Library', icon: Library },
  { label: 'Settings', icon: Settings },
]

const stageLabels = ['Plan', 'Research', 'Script', 'Storyboard', 'Assets', 'Scenes', 'Audio', 'Render', 'Review']

function MetricCard({ metric }: { metric: DashboardSnapshot['metrics'][number] }) {
  return (
    <article className="metric-card">
      <span className="metric-label">{metric.label}</span>
      <strong>{metric.value}</strong>
      <span className={`metric-detail metric-${metric.tone}`}>{metric.detail}</span>
    </article>
  )
}

function EventMarker({ status }: { status: PipelineEvent['status'] }) {
  if (status === 'complete') return <Check aria-hidden="true" size={13} />
  if (status === 'warning') return <CircleAlert aria-hidden="true" size={13} />
  if (status === 'active') return <RefreshCw aria-hidden="true" size={13} />
  return <Clock3 aria-hidden="true" size={13} />
}

function Dashboard({ snapshot }: { snapshot: DashboardSnapshot }) {
  const queryClient = useQueryClient()
  const advanceMutation = useMutation({
    mutationFn: advanceDemoPipeline,
    onSuccess: (data) => queryClient.setQueryData(['dashboard'], data),
  })

  const completedStages = Math.max(1, Math.floor((snapshot.activeEpisode.progress / 100) * stageLabels.length))

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Production overview</p>
          <h1>Good morning, Nagasai.</h1>
          <p className="page-description">Your studio is on schedule. One episode needs your attention.</p>
        </div>
        <div className="header-actions">
          <span className={`mode-badge ${snapshot.mode === 'live' ? 'mode-live' : ''}`}>
            <span className="mode-dot" />
            {snapshot.mode === 'live' ? 'Live workspace' : 'Demo workspace'}
          </span>
          <button className="primary-button" disabled={usesStaticSnapshot || advanceMutation.isPending} onClick={() => advanceMutation.mutate()}>
            <Play aria-hidden="true" size={15} fill="currentColor" />
            Advance simulation
          </button>
        </div>
      </header>

      <section className="metrics-grid" aria-label="Production metrics">
        {snapshot.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
      </section>

      <div className="dashboard-grid">
        <section className="panel active-production">
          <div className="panel-header">
            <div>
              <span className="section-kicker">Active production</span>
              <h2>{snapshot.activeEpisode.title}</h2>
            </div>
            <button className="icon-button" aria-label="Open episode">
              <ArrowRight aria-hidden="true" size={18} />
            </button>
          </div>

          <p className="objective">{snapshot.activeEpisode.objective}</p>

          <div className="production-meta">
            <span><Sparkles aria-hidden="true" size={14} />{snapshot.activeEpisode.format}</span>
            <span><CalendarDays aria-hidden="true" size={14} />{snapshot.activeEpisode.scheduledFor}</span>
            <span><Database aria-hidden="true" size={14} />{snapshot.activeEpisode.cost}</span>
          </div>

          <div className="progress-heading">
            <div>
              <span>{formatState(snapshot.activeEpisode.state)}</span>
              <small>{snapshot.activeEpisode.sceneProgress}</small>
            </div>
            <strong>{snapshot.activeEpisode.progress}%</strong>
          </div>
          <div className="progress-track" aria-label={`${snapshot.activeEpisode.progress}% complete`}>
            <span style={{ width: `${snapshot.activeEpisode.progress}%` }} />
          </div>

          <ol className="stage-row" aria-label="Episode stages">
            {stageLabels.map((stage, index) => (
              <li key={stage} className={index < completedStages ? 'stage-complete' : index === completedStages ? 'stage-current' : ''}>
                <span>{index < completedStages ? <Check aria-hidden="true" size={11} /> : index + 1}</span>
                <small>{stage}</small>
              </li>
            ))}
          </ol>
        </section>

        <section className="panel activity-panel">
          <div className="panel-header compact">
            <div>
              <span className="section-kicker">Agent activity</span>
              <h2>Run timeline</h2>
            </div>
            <button className="text-button">View all</button>
          </div>
          <ol className="event-list">
            {snapshot.events.map((event) => (
              <li key={event.id}>
                <span className={`event-marker event-${event.status}`}><EventMarker status={event.status} /></span>
                <div>
                  <div className="event-title"><strong>{event.title}</strong><time>{event.time}</time></div>
                  <p>{event.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <div className="lower-grid">
        <section className="panel schedule-panel">
          <div className="panel-header compact">
            <div>
              <span className="section-kicker">Release plan</span>
              <h2>Later this week</h2>
            </div>
            <button className="text-button">Open queue</button>
          </div>
          <div className="episode-list">
            {snapshot.upcomingEpisodes.map((episode) => (
              <button className="episode-row" key={episode.id}>
                <span className="episode-date">{episode.scheduledFor.slice(0, 3)}</span>
                <span className="episode-copy"><strong>{episode.title}</strong><small>{episode.objective}</small></span>
                <span className="queue-state">Queued</span>
                <ChevronRight aria-hidden="true" size={16} />
              </button>
            ))}
          </div>
        </section>

        <section className="panel library-panel">
          <div className="panel-header compact">
            <div>
              <span className="section-kicker">Studio memory</span>
              <h2>Library health</h2>
            </div>
            <button className="icon-button subtle" aria-label="Open library"><BookOpen aria-hidden="true" size={17} /></button>
          </div>
          <div className="library-stats">
            <div><strong>{snapshot.library.sources}</strong><span>Active sources</span></div>
            <div><strong>{snapshot.library.reusableAssets}</strong><span>Reusable assets</span></div>
            <div><strong>{snapshot.library.storage}</strong><span>Stored media</span></div>
          </div>
          <div className="library-alert">
            <Archive aria-hidden="true" size={17} />
            <div><strong>{snapshot.library.staleSources} sources need a freshness check</strong><span>{snapshot.library.missingRights} assets are missing rights metadata</span></div>
            <ChevronRight aria-hidden="true" size={16} />
          </div>
        </section>
      </div>

      <footer className="data-footer">
        Snapshot updated {formatGeneratedAt(snapshot.generatedAt)}
      </footer>
    </>
  )
}

export function App() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const dashboardQuery = useQuery({ queryKey: ['dashboard'], queryFn: getDashboardSnapshot, refetchInterval: usesStaticSnapshot ? false : 15_000 })

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <span className="brand-mark"><Bot aria-hidden="true" size={18} /></span>
          <div><strong>Cartoon Studio</strong><small>Production control</small></div>
          <button className="mobile-close" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><X size={18} /></button>
        </div>
        <nav aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, active, count }) => (
            <button key={label} className={active ? 'nav-active' : ''}>
              <Icon aria-hidden="true" size={17} />
              <span>{label}</span>
              {count ? <small>{count}</small> : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-health"><span /><div><strong>Systems nominal</strong><small>All services available</small></div></div>
          <button className="owner-card"><span>NK</span><div><strong>Nagasai</strong><small>Studio owner</small></div><ChevronRight size={15} /></button>
        </div>
      </aside>

      {mobileNavOpen ? <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} /> : null}

      <main>
        <div className="mobile-bar">
          <button className="icon-button" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={18} /></button>
          <strong>Cartoon Studio</strong>
          <button className="icon-button" aria-label="Search"><Search size={18} /></button>
        </div>
        {dashboardQuery.isLoading ? <div className="loading-state"><RefreshCw size={20} /> Loading studio...</div> : null}
        {dashboardQuery.isError ? <div className="error-state"><CircleAlert size={20} /><div><strong>Could not reach the studio API</strong><p>{dashboardQuery.error.message}</p></div></div> : null}
        {dashboardQuery.data ? <Dashboard snapshot={dashboardQuery.data} /> : null}
      </main>
    </div>
  )
}
