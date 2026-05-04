import { useEffect, useState } from 'react'
import {
  Laptop,
  Smartphone,
  Gamepad2,
  Tv,
  Wifi,
  RefreshCw,
  Plus,
  HelpCircle,
  Network,
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
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import type { Device } from '@/lib/types'
import { api, ApiError } from '@/lib/api'
import { useToast } from '@/components/ui/Toaster'
import { cn } from '@/lib/utils'

interface DevicesPanelProps {
  devices: Device[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  refreshedAt: Date | null
}

const TYPE_ICON: Record<string, typeof Wifi> = {
  mobile: Smartphone,
  computer: Laptop,
  console: Gamepad2,
  iot: Tv,
}

const TYPE_OPTIONS = ['mobile', 'computer', 'console', 'iot', 'unknown']

export function DevicesPanel({
  devices,
  loading,
  error,
  refresh,
  refreshedAt,
}: DevicesPanelProps) {
  const [adding, setAdding] = useState(false)

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <Network className="h-4 w-4 text-muted-foreground" />
            Devices on the network
          </CardTitle>
          <CardDescription>
            Live discovery from OpenWRT, merged with manually added entries.
            {refreshedAt && (
              <span className="ml-1 text-xs text-muted-foreground/70">
                · refreshed {formatTime(refreshedAt)}
              </span>
            )}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAdding((v) => !v)}
            disabled={loading}
          >
            <Plus className="h-3.5 w-3.5" />
            Add manually
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void refresh()}
            disabled={loading}
            aria-label="Refresh devices"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {adding && (
          <AddDeviceForm
            onCancel={() => setAdding(false)}
            onAdded={async () => {
              setAdding(false)
              await refresh()
            }}
          />
        )}

        {error ? (
          <ErrorState message={error} onRetry={() => void refresh()} />
        ) : loading && devices.length === 0 ? (
          <DeviceListSkeleton />
        ) : devices.length === 0 ? (
          <EmptyState />
        ) : (
          <DeviceTable devices={devices} />
        )}
      </CardContent>
    </Card>
  )
}

function DeviceTable({ devices }: { devices: Device[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        <div>Device</div>
        <div className="hidden sm:block">Network</div>
        <div>Type</div>
      </div>
      <ul className="divide-y divide-border">
        {devices.map((d) => {
          const Icon = TYPE_ICON[d.type] ?? HelpCircle
          return (
            <li
              key={d.id}
              className="grid grid-cols-[1fr_auto_auto] items-center gap-4 px-4 py-3 transition-colors hover:bg-muted/20"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{d.name}</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">
                    {d.mac || 'no MAC'}
                  </div>
                </div>
              </div>
              <div className="hidden font-mono text-xs text-muted-foreground sm:block">
                {d.ip ?? '—'}
              </div>
              <Badge variant="outline" className="capitalize">
                {d.type}
              </Badge>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function DeviceListSkeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-md border border-border px-4 py-3"
        >
          <Skeleton className="h-9 w-9 rounded-md" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-2.5 w-44" />
          </div>
          <Skeleton className="h-5 w-14" />
        </div>
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-border py-10 text-center">
      <Wifi className="h-6 w-6 text-muted-foreground" />
      <p className="mt-2 text-sm font-medium">No devices yet</p>
      <p className="mt-1 max-w-sm text-xs text-muted-foreground">
        Connect a client to your router or add one manually below to start applying intents.
      </p>
    </div>
  )
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-4">
      <div className="flex-1">
        <p className="text-sm font-medium text-destructive">Could not load devices</p>
        <p className="mt-1 text-xs text-muted-foreground">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </Button>
    </div>
  )
}

function AddDeviceForm({
  onCancel,
  onAdded,
}: {
  onCancel: () => void
  onAdded: () => Promise<void>
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [type, setType] = useState('mobile')
  const [mac, setMac] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => setErr(null), [name, type, mac])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setErr('Name is required.')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/devices', { name: name.trim(), type, mac: mac.trim() })
      toast({ title: 'Device added', description: name.trim(), variant: 'success' })
      await onAdded()
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : 'Could not add device.'
      setErr(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid grid-cols-1 gap-3 rounded-md border border-border bg-muted/20 p-4 sm:grid-cols-[1fr_140px_180px_auto]"
    >
      <div className="space-y-1.5">
        <Label htmlFor="add-name">Name</Label>
        <Input
          id="add-name"
          placeholder="Living room TV"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="add-type">Type</Label>
        <Select id="add-type" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="add-mac">MAC (optional)</Label>
        <Input
          id="add-mac"
          placeholder="AA:BB:CC:DD:EE:FF"
          value={mac}
          onChange={(e) => setMac(e.target.value)}
          className="font-mono"
        />
      </div>
      <div className="flex items-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={submitting}>
          {submitting ? 'Adding…' : 'Add device'}
        </Button>
      </div>
      {err && <p className="text-xs text-destructive sm:col-span-4">{err}</p>}
    </form>
  )
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
