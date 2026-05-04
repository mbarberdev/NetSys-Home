import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import type { Device } from '@/lib/types'

export function useDevices() {
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<Device[]>('/devices')
      setDevices(Array.isArray(data) ? data : [])
      setRefreshedAt(new Date())
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Unable to load devices.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { devices, loading, error, refresh, refreshedAt }
}
