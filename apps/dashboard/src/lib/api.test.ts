import { afterEach, describe, expect, it, vi } from 'vitest'

import { demoSnapshot } from '../demo-data'
import { getDashboardSnapshot } from './api'

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 404,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

describe('getDashboardSnapshot', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('loads the generated GitHub Pages snapshot', async () => {
    const generatedSnapshot = {
      ...demoSnapshot,
      generatedAt: '2026-09-04T06:00:00Z',
    }
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(generatedSnapshot))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getDashboardSnapshot()).resolves.toEqual(generatedSnapshot)
    expect(fetchMock).toHaveBeenCalledWith(`${import.meta.env.BASE_URL}data/dashboard.json`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
  })

  it('uses bundled demo data when generated data is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({}, false)))

    await expect(getDashboardSnapshot()).resolves.toEqual(demoSnapshot)
  })

  it('uses bundled demo data when generated data is invalid', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({ mode: 'demo' })))

    await expect(getDashboardSnapshot()).resolves.toEqual(demoSnapshot)
  })
})
