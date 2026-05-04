import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import type { Policy } from '@/lib/types'

export function usePolicies() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<Policy[]>('/policies')
      setPolicies(Array.isArray(data) ? data : [])
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Unable to load policies.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  const remove = useCallback(
    async (id: number) => {
      await api.delete(`/policies/${id}`)
      await refresh()
    },
    [refresh],
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { policies, loading, error, refresh, remove }
}
