import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import type { AppStatus } from '@/lib/types'

const POLL_INTERVAL_MS = 15_000

export function useStatus() {
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api.get<AppStatus>('/status')
      setStatus(data)
      setError(null)
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Backend unreachable.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    timer.current = window.setInterval(refresh, POLL_INTERVAL_MS)
    return () => {
      if (timer.current !== null) window.clearInterval(timer.current)
    }
  }, [refresh])

  return { status, loading, error, refresh }
}
