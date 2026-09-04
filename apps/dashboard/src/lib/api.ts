import { demoSnapshot } from '../demo-data'
import type { DashboardSnapshot } from '../types'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')

export const isDemoMode = !configuredApiBaseUrl

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!configuredApiBaseUrl) {
    return demoSnapshot
  }

  const response = await fetch(`${configuredApiBaseUrl}/api/v1/dashboard`, {
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Dashboard API returned ${response.status}`)
  }

  return (await response.json()) as DashboardSnapshot
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

  return (await response.json()) as DashboardSnapshot
}
