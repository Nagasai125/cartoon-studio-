import { describe, expect, it } from 'vitest'

import { formatGeneratedAt, formatState } from './format'

describe('formatState', () => {
  it('turns pipeline identifiers into readable labels', () => {
    expect(formatState('scene_production')).toBe('Scene Production')
    expect(formatState('needs_approval')).toBe('Needs Approval')
  })
})

describe('formatGeneratedAt', () => {
  it('does not throw when snapshot data contains an invalid timestamp', () => {
    expect(formatGeneratedAt('invalid')).toBe('at an unknown time')
  })
})
