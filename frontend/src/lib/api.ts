export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail || `Request failed with status ${status}`)
    this.status = status
    this.detail = detail
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg
    if (typeof body?.error === 'string') return body.error
    return JSON.stringify(body)
  } catch {
    return response.statusText
  }
}

export async function apiRequest<T = unknown>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const normalized = path.startsWith('/') ? path : `/${path}`
  const response = await fetch(`/api${normalized}`, options)

  if (!response.ok) {
    const detail = await parseError(response)
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  get: <T,>(path: string) => apiRequest<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T,>(path: string) =>
    apiRequest<T>(path, { method: 'DELETE' }),
}
