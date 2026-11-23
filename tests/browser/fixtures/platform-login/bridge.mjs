import { ref } from 'vue'
const cache = window.testCache ||= new Map()
export const useCache = () => ({ wsCache: { get: k => cache.get(k), set: (k, v) => cache.set(k,v), delete: k => cache.delete(k) } })
export const useAssistantStore = () => ({ getToken: '', getAssistant: null })
window.testUser ||= { token: '', exp: null }
export const useUserStore = () => ({
  setToken: v => { window.testUser.token = v }, setExp: v => { window.testUser.exp = v },
  setTime() {}, setPlatformInfo() {},
})
const router = { currentRoute: ref({ name: 'login', query: {} }), push: v => { window.testRoute = v } }
export default router
export const useRouter = () => router
export const getQueryString = k => new URLSearchParams(location.search).get(k)
export const getUrlParams = () => Object.fromEntries(new URLSearchParams(location.search))
export const getSQLBotAddr = () => location.origin + location.pathname
export const isPlatformClient = () => false
export const getLocale = () => new URLSearchParams(location.search).get('lang') || 'zh-CN'
export const loadClient = () => false
export const origin_mapping = { 6: 'wecom' }
