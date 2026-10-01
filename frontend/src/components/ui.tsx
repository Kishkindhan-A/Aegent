import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

export function Button({ children, variant = 'primary', loading, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; loading?: boolean }) {
  return <button className={`button button-${variant}`} disabled={loading || props.disabled} {...props}>{loading ? 'Working...' : children}</button>
}

export function Field({ label, error, hint, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }) {
  const id = props.id || props.name
  return <div className="field"><label htmlFor={id}>{label}</label><input id={id} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined} {...props} />{hint && !error && <span className="field-hint" id={`${id}-hint`}>{hint}</span>}{error && <span className="field-error" id={`${id}-error`} role="alert">{error}</span>}</div>
}

export function Notice({ children, tone = 'error' }: { children: ReactNode; tone?: 'error' | 'success' | 'info' }) { return <div className={`notice notice-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{children}</div> }

export function LoadingState({ label = 'Loading workspace' }: { label?: string }) { return <div className="loading-state" role="status"><span className="loader" aria-hidden="true" />{label}</div> }