import { AppShell } from '@/components/AppShell'
import { DevicesPanel } from '@/components/DevicesPanel'
import { IntentPanel } from '@/components/IntentPanel'
import { PoliciesPanel } from '@/components/PoliciesPanel'
import { ToastProvider } from '@/components/ui/Toaster'
import { useDevices } from '@/hooks/useDevices'
import { usePolicies } from '@/hooks/usePolicies'
import { useStatus } from '@/hooks/useStatus'

export function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  )
}

function AppContent() {
  const { status, error: statusError } = useStatus()
  const devicesState = useDevices()
  const policiesState = usePolicies()

  return (
    <AppShell status={status} statusError={statusError}>
      <Hero status={status} statusError={statusError} />

      <DevicesPanel
        devices={devicesState.devices}
        loading={devicesState.loading}
        error={devicesState.error}
        refresh={devicesState.refresh}
        refreshedAt={devicesState.refreshedAt}
      />

      <IntentPanel
        devices={devicesState.devices}
        loadingDevices={devicesState.loading}
        onApplied={async () => {
          await Promise.all([devicesState.refresh(), policiesState.refresh()])
        }}
      />

      <PoliciesPanel
        policies={policiesState.policies}
        devices={devicesState.devices}
        loading={policiesState.loading}
        error={policiesState.error}
        refresh={policiesState.refresh}
        remove={policiesState.remove}
      />
    </AppShell>
  )
}

function Hero({
  status,
  statusError,
}: {
  status: ReturnType<typeof useStatus>['status']
  statusError: string | null
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="text-2xl font-semibold tracking-tight">Network control</h1>
      <p className="text-sm text-muted-foreground">
        {statusError
          ? 'Backend is unreachable — start the FastAPI server with `python3 app.py`.'
          : status?.openwrt === 'connected'
            ? `Connected to ${status.hostname ?? 'OpenWRT'} · ${status.model ?? ''} · firmware ${status.version ?? ''}`.trim()
            : 'OpenWRT router is offline. Policies will still be saved locally and enforced when the router comes back.'}
      </p>
    </div>
  )
}
