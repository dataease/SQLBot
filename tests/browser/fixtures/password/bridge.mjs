// Only session/store boundaries are replaced; the real auth API and HTTP client run.
export const useAssistantStore = () => ({})
export const useCache = () => ({ wsCache: { get: () => undefined, delete: () => {} } })
export const getLocale = () => new URLSearchParams(location.search).get('lang') || 'zh-CN'
export const useRouter = () => ({})
