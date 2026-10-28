// Replace only the request boundary; no actual authentication configuration is changed.
export const getSQLBotAddr = () => location.origin + location.pathname
window.savedConfigs = []
export const request = {
  get: async () => null,
  patch: async () => true,
  post: async (url, data) => { window.savedConfigs.push(data); return 1 },
  put: async (url, data) => { window.savedConfigs.push(data); return 1 },
}
