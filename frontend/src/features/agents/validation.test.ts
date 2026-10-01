import { describe, expect, it } from 'vitest'
import { canManageAgents, validateScanContent } from './validation'

describe('agent workspace validation', () => {
  it('keeps MEMBER mutation controls disabled while allowing management roles', () => {
    expect(canManageAgents('MEMBER')).toBe(false)
    expect(canManageAgents('OWNER')).toBe(true)
    expect(canManageAgents('SECURITY_ANALYST')).toBe(true)
  })

  it('accepts 19,999 and 20,000 scan characters but rejects 20,001', () => {
    expect(validateScanContent('x'.repeat(19999))).toBe('')
    expect(validateScanContent('x'.repeat(20000))).toBe('')
    expect(validateScanContent('x'.repeat(20001))).toContain('20,000')
  })
})