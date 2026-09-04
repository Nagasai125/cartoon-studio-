import { describe, expect, it } from 'vitest'

import { formatState } from './format'

describe('formatState', () => {
  it('turns pipeline identifiers into readable labels', () => {
    expect(formatState('scene_production')).toBe('Scene Production')
    expect(formatState('needs_approval')).toBe('Needs Approval')
  })
})
