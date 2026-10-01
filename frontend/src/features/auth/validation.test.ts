import { describe, expect, it } from 'vitest'
import { validateLogin, validateRegistration } from './validation'

describe('auth validation', () => {
  it('requires tenant-aware login fields', () => {
    expect(validateLogin({ organization: '', email: 'bad', password: '' })).toEqual({ organization: 'Organization slug is required.', email: 'Enter a valid email address.', password: 'Password is required.' })
  })
  it('rejects unsafe organization slugs and short passwords', () => {
    const errors = validateRegistration({ organizationName: 'Acme', organizationSlug: 'Acme Security', ownerName: 'Owner', email: 'owner@acme.test', password: 'short' })
    expect(errors.organizationSlug).toBe('Use lowercase letters, numbers, and hyphens.')
    expect(errors.password).toBe('Password must be at least 8 characters.')
  })
})