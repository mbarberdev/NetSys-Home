import { useEffect, useMemo, useState } from 'react'
import { Sparkles, Wand2, AlertTriangle, ArrowRight } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toaster'
import { useDebounced } from '@/hooks/useDebounced'
import { api, ApiError } from '@/lib/api'
import {
  ACTION_DESCRIPTIONS,
  ACTION_LABELS,
  type Action,
  type ClassifyResponse,
  type Device,
  type IntentResponse,
} from '@/lib/types'
import { cn } from '@/lib/utils'

interface IntentPanelProps {
  devices: Device[]
  loadingDevices: boolean
  onApplied: () => Promise<void>
}

const ACTION_VALUES: Action[] = ['block', 'isolate', 'guest_network', 'schedule_block']

export function IntentPanel({ devices, loadingDevices, onApplied }: IntentPanelProps) {
  const { toast } = useToast()
  const [deviceId, setDeviceId] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [action, setAction] = useState<Action>('block')
  const [time, setTime] = useState('22:00')
  const [classification, setClassification] = useState<ClassifyResponse | null>(null)
  const [classifying, setClassifying] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<IntentResponse | null>(null)

  const debouncedText = useDebounced(text, 400)

  // First-device default
  useEffect(() => {
    if (deviceId === null && devices.length > 0) setDeviceId(devices[0].id)
  }, [devices, deviceId])

  // Live classification
  useEffect(() => {
    const trimmed = debouncedText.trim()
    if (!trimmed) {
      setClassification(null)
      return
    }
    let cancelled = false
    setClassifying(true)
    api.post<ClassifyResponse>('/classify', { text: trimmed })
      .then((res) => {
        if (cancelled) return
        setClassification(res)
        setAction(res.predicted_action)
      })
      .catch(() => {
        if (cancelled) return
        setClassification(null)
      })
      .finally(() => {
        if (!cancelled) setClassifying(false)
      })
    return () => {
      cancelled = true
    }
  }, [debouncedText])

  const selectedDevice = useMemo(
    () => devices.find((d) => d.id === deviceId) ?? null,
    [devices, deviceId],
  )
  const macWarning = !!selectedDevice && !selectedDevice.mac && action !== 'guest_network'
  const noDevices = !loadingDevices && devices.length === 0

  async function submit() {
    setError(null)
    if (deviceId === null) {
      setError('Pick a device first.')
      return
    }
    if (action === 'schedule_block' && !time.trim()) {
      setError('Schedule needs a time (HH:MM).')
      return
    }
    setSubmitting(true)
    try {
      const body: Record<string, unknown> = { device_id: deviceId }
      if (text.trim()) body.text = text.trim()
      else body.action = action
      if (action === 'schedule_block') body.time = time

      const res = await api.post<IntentResponse>('/intent', body)
      setLastResult(res)

      toast({
        title: res.enforced ? 'Intent applied' : 'Intent saved (router offline)',
        description: res.rule,
        variant: res.enforced ? 'success' : 'warning',
      })
      await onApplied()

      // Reset on success — keep device + action so the user can chain intents
      setText('')
      setClassification(null)
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : 'Unable to apply the intent.'
      setError(msg)
      toast({ title: 'Failed to apply intent', description: msg, variant: 'destructive' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-muted-foreground" />
          Create an intent
        </CardTitle>
        <CardDescription>
          Describe what you want in plain English, or pick an action directly. The ML
          classifier will pre-fill the action when you type.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_minmax(0,1fr)]">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="intent-text">Describe (optional)</Label>
              <div className="relative">
                <Input
                  id="intent-text"
                  placeholder="e.g. block my gaming console after 10pm"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  className="pr-9"
                />
                {classifying && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <span className="block h-3 w-3 animate-pulse rounded-full bg-primary" />
                  </div>
                )}
              </div>
              {classification && (
                <div
                  className="flex animate-fade-in items-center gap-2 text-xs text-muted-foreground"
                >
                  <Sparkles className="h-3 w-3 text-primary" />
                  Detected{' '}
                  <Badge variant="default" className="capitalize">
                    {ACTION_LABELS[classification.predicted_action]}
                  </Badge>
                  <ConfidenceMeter value={classification.confidence ?? 0} />
                </div>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="intent-device">Device</Label>
              <Select
                id="intent-device"
                value={deviceId ?? ''}
                onChange={(e) => setDeviceId(Number(e.target.value))}
                disabled={loadingDevices || noDevices}
              >
                {noDevices ? (
                  <option>(no devices yet)</option>
                ) : (
                  devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                      {d.mac ? ` — ${d.mac}` : ''}
                    </option>
                  ))
                )}
              </Select>
              {macWarning && (
                <p className="flex items-start gap-1.5 text-xs text-warning">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                  This device has no MAC, so the policy will be saved but cannot be enforced
                  on the router. Add a MAC to enable enforcement.
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="intent-action">Action</Label>
                <Select
                  id="intent-action"
                  value={action}
                  onChange={(e) => setAction(e.target.value as Action)}
                >
                  {ACTION_VALUES.map((a) => (
                    <option key={a} value={a}>
                      {ACTION_LABELS[a]}
                    </option>
                  ))}
                </Select>
              </div>
              {action === 'schedule_block' && (
                <div className="space-y-1.5">
                  <Label htmlFor="intent-time">Block after</Label>
                  <Input
                    id="intent-time"
                    type="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                  />
                </div>
              )}
            </div>

            {error && (
              <p className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            <div className="flex items-center gap-3 pt-1">
              <Button onClick={submit} disabled={submitting || noDevices || deviceId === null}>
                {submitting ? 'Applying…' : 'Apply intent'}
                {!submitting && <ArrowRight className="h-4 w-4" />}
              </Button>
              <p className="text-xs text-muted-foreground">
                {ACTION_DESCRIPTIONS[action]}
              </p>
            </div>
          </div>

          <ResultPanel result={lastResult} action={action} />
        </div>
      </CardContent>
    </Card>
  )
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const tone =
    value >= 0.7 ? 'bg-success' : value >= 0.4 ? 'bg-warning' : 'bg-destructive'
  return (
    <span className="flex items-center gap-1">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <span
          className={cn('block h-full transition-all', tone)}
          style={{ width: `${Math.max(4, pct)}%` }}
        />
      </span>
      <span className="tabular-nums">{pct}%</span>
    </span>
  )
}

function ResultPanel({
  result,
  action,
}: {
  result: IntentResponse | null
  action: Action
}) {
  if (!result) {
    return (
      <div className="flex h-full min-h-[200px] flex-col items-start justify-center rounded-md border border-dashed border-border bg-muted/10 p-6">
        <Badge variant="muted">Preview</Badge>
        <p className="mt-3 text-sm font-medium">{ACTION_LABELS[action]}</p>
        <p className="mt-1 text-xs text-muted-foreground">{ACTION_DESCRIPTIONS[action]}</p>
      </div>
    )
  }
  return (
    <div className="flex h-full min-h-[200px] flex-col rounded-md border border-border bg-muted/10 p-6">
      <div className="flex items-center gap-2">
        <Badge variant={result.enforced ? 'success' : 'warning'}>
          {result.enforced ? 'Enforced on router' : 'Saved · not enforced'}
        </Badge>
        <Badge variant="outline">#{result.id}</Badge>
      </div>
      <p className="mt-3 text-sm font-medium leading-snug">{result.rule}</p>
      {result.classification && (
        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
          <Sparkles className="h-3 w-3 text-primary" />
          ML predicted <span className="font-medium">{result.classification.predicted_action}</span>
          {result.classification.confidence !== null && (
            <span>· {Math.round(result.classification.confidence * 100)}% confidence</span>
          )}
        </div>
      )}
      <p className="mt-auto pt-3 text-xs text-muted-foreground">
        Created {formatRelative(result.created_at)}
      </p>
    </div>
  )
}

function formatRelative(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}
