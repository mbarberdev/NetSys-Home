async function parseJsonResponse(response) {
  const contentType = response.headers.get('content-type') || ''

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  if (!contentType.includes('application/json')) {
    throw new Error(`Expected JSON but received ${contentType || 'unknown content type'}`)
  }

  return response.json()
}

async function fetchJson(url, options) {
  const response = await fetch(url, options)
  return parseJsonResponse(response)
}

export async function apiRequest(path, options) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return fetchJson(`/api${normalizedPath}`, options)
}
