const call = async (method, url, data) => {
  const response = await fetch('/api' + url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: method === 'GET' ? undefined : JSON.stringify(data),
  })
  if (!response.ok) throw new Error('fixture request failed')
  return response.json()
}
export const request = {
  get: (url, config) => call('GET', url + '?' + new URLSearchParams(config?.params)),
  post: (url, data) => call('POST', url, data),
  put: (url, data) => call('PUT', url, data),
}
