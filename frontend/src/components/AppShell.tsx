import { useState, useEffect, type ReactNode } from 'react'
import { Activity, Cpu, LayoutDashboard, Moon, Network, Sun, Wifi } from 'lucide-react'
import type { AppStatus } from '@/lib/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface AppShellProps {
  status: AppStatus | null
  statusError: string | null
  children: ReactNode
}

export function AppShell({ status, statusError, children }: AppShellProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('netsys-theme') as 'dark' | 'light') ?? 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
      root.style.colorScheme = 'dark'
    } else {
      root.classList.remove('dark')
      root.style.colorScheme = 'light'
    }
    localStorage.setItem('netsys-theme', theme)
  }, [theme])

  function toggleTheme() {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            status={status}
            statusError={statusError}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
          <main className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
            <div className="mx-auto w-full max-w-6xl space-y-8">{children}</div>
          </main>
        </div>
      </div>
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-card/30 lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Network className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-none">NetSys Home</div>
          <div className="mt-1 text-[11px] uppercase tracking-wider text-muted-foreground">
            v1.0
          </div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3 py-4 text-sm">
        <NavItem icon={<LayoutDashboard className="h-4 w-4" />} active>
          Dashboard
        </NavItem>
        <NavItem icon={<Wifi className="h-4 w-4" />}>Devices</NavItem>
        <NavItem icon={<Activity className="h-4 w-4" />}>Policies</NavItem>
        <NavItem icon={<Cpu className="h-4 w-4" />}>System</NavItem>
      </nav>
      <div className="border-t border-border p-3 text-xs text-muted-foreground">
        Intent-based home Wi-Fi management.
      </div>
    </aside>
  )
}

function NavItem({
  icon,
  children,
  active = false,
}: {
  icon: ReactNode
  children: ReactNode
  active?: boolean
}) {
  return (
    <a
      href="#"
      className={cn(
        'flex items-center gap-2 rounded-md px-3 py-2 text-foreground/80 transition-colors',
        active
          ? 'bg-secondary text-foreground'
          : 'hover:bg-secondary/60 hover:text-foreground',
      )}
      onClick={(e) => e.preventDefault()}
    >
      {icon}
      {children}
    </a>
  )
}

function TopBar({
  status,
  statusError,
  theme,
  onToggleTheme,
}: {
  status: AppStatus | null
  statusError: string | null
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}) {
  const routerOk = status?.openwrt === 'connected'
  const classifierOk = status?.classifier && status.classifier !== 'stub'

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/80 px-6 backdrop-blur lg:px-10">
      <div className="flex items-center gap-3">
        <div className="lg:hidden flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Network className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">NetSys Home</span>
        </div>
        <div className="hidden lg:block">
          <h1 className="text-sm font-medium text-muted-foreground">Dashboard</h1>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {statusError ? (
          <Badge variant="destructive" title={statusError}>
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-destructive" />
            API offline
          </Badge>
        ) : (
          <>
            <Badge variant={routerOk ? 'success' : 'muted'}>
              <span
                className={cn(
                  'inline-block h-1.5 w-1.5 rounded-full',
                  routerOk ? 'bg-success' : 'bg-muted-foreground/60',
                )}
              />
              Router {routerOk ? 'connected' : 'offline'}
              {status?.version ? ` · ${status.version}` : ''}
            </Badge>
            <Badge variant={classifierOk ? 'default' : 'warning'}>
              <Cpu className="h-3 w-3" />
              {classifierOk ? 'ML active' : 'Classifier stub'}
            </Badge>
            <Badge variant="outline">v{status?.app_version ?? '—'}</Badge>
          </>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  )
}
