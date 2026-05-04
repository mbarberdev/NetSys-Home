import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export type ToastVariant = 'default' | 'success' | 'destructive' | 'warning'

export interface Toast {
  id: number
  title: string
  description?: string
  variant?: ToastVariant
}

interface ToastContextValue {
  toast: (t: Omit<Toast, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    ({ title, description, variant = 'default' }: Omit<Toast, 'id'>) => {
      const id = nextId++
      setToasts((prev) => [...prev, { id, title, description, variant }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[]
  onDismiss: (id: number) => void
}) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const t = window.setTimeout(() => setLeaving(true), 4200)
    return () => window.clearTimeout(t)
  }, [])

  const variant = toast.variant ?? 'default'
  const Icon =
    variant === 'success' ? CheckCircle2
    : variant === 'destructive' ? AlertCircle
    : variant === 'warning' ? AlertCircle
    : Info

  return (
    <div
      role="status"
      className={cn(
        'pointer-events-auto flex items-start gap-3 rounded-lg border bg-card p-3 pr-2 shadow-lg transition-all duration-200',
        'animate-fade-in',
        variant === 'success' && 'border-success/40',
        variant === 'destructive' && 'border-destructive/40',
        variant === 'warning' && 'border-warning/40',
        leaving && 'translate-x-2 opacity-0',
      )}
    >
      <Icon
        className={cn(
          'mt-0.5 h-4 w-4 shrink-0',
          variant === 'success' && 'text-success',
          variant === 'destructive' && 'text-destructive',
          variant === 'warning' && 'text-warning',
          variant === 'default' && 'text-muted-foreground',
        )}
      />
      <div className="flex-1 text-sm">
        <div className="font-medium leading-tight">{toast.title}</div>
        {toast.description && (
          <div className="mt-0.5 text-muted-foreground">{toast.description}</div>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        aria-label="Dismiss"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
