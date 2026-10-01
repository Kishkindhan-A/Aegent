export function validateLogin(values: { organization: string; email: string; password: string }) {
  const errors: Record<string, string> = {}
  if (!values.organization.trim()) errors.organization = 'Organization slug is required.'
  if (!values.email.trim()) errors.email = 'Email is required.'
  if (!values.email.includes('@')) errors.email = 'Enter a valid email address.'
  if (!values.password) errors.password = 'Password is required.'
  return errors
}

export function validateRegistration(values: { organizationName: string; organizationSlug: string; ownerName: string; email: string; password: string }) {
  const errors: Record<string, string> = {}
  if (!values.organizationName.trim()) errors.organizationName = 'Organization name is required.'
  if (!values.organizationSlug.trim()) errors.organizationSlug = 'Organization slug is required.'
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(values.organizationSlug)) errors.organizationSlug = 'Use lowercase letters, numbers, and hyphens.'
  if (!values.ownerName.trim()) errors.ownerName = 'Your name is required.'
  if (!values.email.includes('@')) errors.email = 'Enter a valid email address.'
  if (values.password.length < 8) errors.password = 'Password must be at least 8 characters.'
  return errors
}