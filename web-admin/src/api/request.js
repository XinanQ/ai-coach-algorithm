const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function request(path, options = {}) {
  const token = localStorage.getItem('authToken')
  const { headers: optionHeaders = {}, body, ...restOptions } = options
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...restOptions,
    body,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { 'X-Auth-Token': token } : {}),
      ...optionHeaders
    }
  })

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  const data = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const message =
        typeof data === 'object'
            ? data.message || data.error || JSON.stringify(data)
            : data || `请求失败：${response.status}`

    throw new Error(message)
  }

  return data
}

export function mockResolve(data) {
  try {
    return Promise.resolve(structuredClone(data))
  } catch {
    return Promise.resolve(JSON.parse(JSON.stringify(data)))
  }
}