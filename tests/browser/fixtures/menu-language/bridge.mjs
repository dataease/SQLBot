// Only account/network, storage and unrelated URL helpers are isolated.
// Menu, route definitions, Pinia actions and translations use production code.
const values = new Map([['user.language', 'en']])
export const useCache = () => ({ wsCache: {
  get: key => values.get(key),
  set: (key, value) => values.set(key, value),
  delete: key => values.delete(key)
} })
export const getBrowserLocale = () => 'en'
export const getCurrentRouter = () => ''
export const getQueryString = () => ''
export const getSQLBotAddr = () => ''
export const isPlatform = () => false
let account = { id: 41, language: 'en', weight: 1 }
export const selectAccount = value => { account = value }
export const AuthApi = {
  login: async () => ({ access_token: 'synthetic-menu-test-token' }),
  logout: async () => null,
  info: async () => ({ account: 'synthetic', name: 'Test', oid: 1, origin: 0, exp: 0, time: 0, ...account })
}
