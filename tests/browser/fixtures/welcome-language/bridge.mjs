import { reactive } from 'vue'
import { i18n } from '@/i18n'

export const getBrowserLocale = () => 'zh-CN'
export const useCache = () => ({ wsCache: { get: () => undefined } })
export const isBtnShow = value => value === '0'
export const setCurrentColor = () => {}
export const db = { assistant: {}, appearance: [], saved: [] }
export const appearance = reactive({
  themeColor: 'default', pc_welcome: undefined, pc_welcome_desc: undefined,
  slogan: undefined, showSlogan: '0',
  get getShowSlogan() { return isBtnShow(this.showSlogan ?? '0') },
  setLoaded() {}, async setAppearance() {
    for (const key of ['pc_welcome', 'pc_welcome_desc', 'slogan', 'showSlogan']) this[key] = db.appearance.find(row => row.pkey === key)?.pval
  }
})
export const useAppearanceStoreWithOut = () => appearance
export const assistant = reactive({
  type: 0, assistant: false, getHistory: true,
  get getAssistant() { return this.assistant },
  get getEmbedded() { return this.assistant && this.type === 4 },
  setPageEmbedded() {}, setType(type) { this.type = type },
  setAssistant(value) { this.assistant = value }, setHistory(value) { this.getHistory = value },
  setToken() {}, setCertificate() {}, resolveCertificate() {}, setHostOrigin() {}, setOnline() {}, setId() {}, setAutoDs() {}
})
export const useAssistantStore = () => assistant
export const useUserStore = () => ({ setLanguage: language => { i18n.global.locale.value = language }, info: async () => {} })
export const request = {
  async get() { return db.appearance },
  async patch(url, data) {
    db.assistant = JSON.parse(data.get('data'))
    db.saved.push({ url, data: db.assistant })
  },
  async post(url, data) {
    db.appearance = JSON.parse(data.get('data'))
    db.saved.push({ url, data: db.appearance })
  }
}
