import { useState } from 'react'
import {
  ShieldCheck,
  Trash2,
  Ban,
  Shield,
  CalendarClock,
  Wifi,
  RefreshCw,
} from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { AlertDialog } from '@/components/ui/AlertDialog'
import type { Device, Policy } from '@/lib/types'
import { useToast } from '@/components/ui/Toaster'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

interface PoliciesPanelProps {
  policies: Policy[]
  devices: Device[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  remove: (id: number) => Promise<void>
}

const ACTION_ICON: Record<string, typeof Shield> = {
  block: Ban,
  isolate: Shield,
  guest_network: Wifi,
  schedule_block: CalendarClock,
}

const ACTION_TONE: Record<string, 'destructive' | 'warning' | 'default' | 'secondary'> = {
  block: 'destructive',
  isolate: 'warning',
  guest_network: 'default',
  schedule_block: 'secondary',
}

export function PoliciesPanel({
  policies,
  devices,
  loading,
  error,
  refresh,
  remove,
}: PoliciesPanelProps) {
  const { toast } = useToast()
  const [removingId, setRemovingId] = useState<number | null>(null)
  const [confirmPolicy, setConfirmPolicy] = useState<Policy | null>(null)

  async function confirmRemove() {
    if (!confirmPolicy) return
    const p = confirmPolicy
    setConfirmPolicy(null)
    setRemovingId(p.id)
    try {
      await remove(p.id)
      toast({ title: 'Policy removed', description: p.rule, variant: 'default' })
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : 'Could not remove policy.'
      toast({ title: 'Failed to remove policy', description: msg, variant: 'destructive' })
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <>
    <AlertDialog
      open={confirmPolicy !== null}
      title="Remove policy?"
      description={confirmPolicy?.rule}
      confirmLabel="Remove"
      variant="destructive"
      onConfirm={() => void confirmRemove()}
      onCancel={() => setConfirmPolicy(null)}
    />
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            Active policies
            {policies.length > 0 && (
              <Badge variant="muted" className="ml-1">
                {policies.length}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Stored locally and enforced on the OpenWRT router whenever it's reachable.
          </CardDescription>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => void refresh()}
          disabled={loading}
          aria-label="Refresh policies"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            {error}
          </div>
        ) : loading && policies.length === 0 ? (
          <PolicySkeleton />
        ) : policies.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="space-y-2">
            {policies.map((p) => {
              const Icon = ACTION_ICON[p.action] ?? Shield
              const tone = ACTION_TONE[p.action] ?? 'secondary'
              const device = devices.find((d) => d.id === p.device_id)
              return (
                <li
                  key={p.id}
                  className="flex items-start gap-3 rounded-md border border-border bg-muted/10 p-3 transition-colors hover:bg-muted/20"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={tone} className="capitalize">
                        {p.action.replace('_', ' ')}
                      </Badge>
                      {device && (
                        <Badge variant="outline" className="text-foreground/70">
                          {device.name}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatRelative(p.created_at)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-snug">{p.rule}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setConfirmPolicy(p)}
                    disabled={removingId === p.id}
                    aria-label={`Remove policy ${p.id}`}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
    </>
  )
}

function PolicySkeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-md border border-border p-3"
        >
          <Skeleton className="h-9 w-9 rounded-md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-2.5 w-full max-w-md" />
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-border py-10 text-center">
      <ShieldCheck className="h-6 w-6 text-muted-foreground" />
      <p className="mt-2 text-sm font-medium">No policies yet</p>
      <p className="mt-1 max-w-sm text-xs text-muted-foreground">
        Apply an intent above to create your first rule. Policies persist across restarts.
      </p>
    </div>
  )
}

function formatRelative(iso: string): string {
  try {
    const d = new Date(iso)
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return d.toLocaleDateString()
  } catch {
    return iso
  }
}
