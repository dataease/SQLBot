import { defineStore } from 'pinia'
// import { ref } from 'vue'
import { AuthApi } from '@/api/login'
import { useCache } from '@/utils/useCache'
import { i18n } from '@/i18n'
import { store } from './index'
import { getCurrentRouter, getQueryString, isPlatform } from '@/utils/utils'

const { wsCache } = useCache()

interface UserState {
  token: string
  uid: string
  account: string
  name: string
  oid: string
  language: string
  exp: number
  time: number
  weight: number
  origin: number
  platformInfo: any | null
  [key: string]: string | number | any | null
}

export const UserStore = defineStore('user', {
  state: (): UserState => {
    return {
      token: '',
      uid: '',
      account: '',
      name: '',
      oid: '',
      language: 'zh-CN',
      exp: 0,
      time: 0,
      weight: 0,
      origin: 0,
      platformInfo: null,
    }
  },
  getters: {
    getToken(): string {
      return this.token
    },
    getUid(): string {
      return this.uid
    },
    getAccount(): string {
      return this.account
    },
    getName(): string {
      return this.name
    },
    getOid(): string {
      return this.oid
    },
    getLanguage(): string {
      return this.language
    },
    getExp(): number {
      return this.exp
    },
    getTime(): number {
      return this.time
    },
    isAdmin(): boolean {
      return this.uid === '1'
    },
    getWeight(): number {
      return this.weight
    },
    getOrigin(): number {
      return this.origin
    },
    isSpaceAdmin(): boolean {
      return this.uid === '1' || !!this.weight
    },
    getPlatformInfo(): any | null {
      return this.platformInfo
    },
  },
  actions: {
    async login(formData: { username: string; password: string }) {
      const res: any = await AuthApi.login(formData)
      this.setToken(res.access_token)
    },

    async logout() {
      let param = { token: this.token }
      if (wsCache.get('user.platformInfo')) {
        param = { ...param, ...wsCache.get('user.platformInfo') }
      }
      const res: any = await AuthApi.logout(param)
      this.clear()
      if (res) {
        window.location.href = res
        window.open(res, '_self')
        return res
      }
      if (
        (getQueryString('code') && getQueryString('state')?.includes('oauth2_state')) ||
        isPlatform()
      ) {
        const currentPath = getCurrentRouter()
        let logout_url = location.origin + location.pathname + '#/login'
        if (currentPath) {
          logout_url += `?redirect=${currentPath}`
        }
        window.location.href = logout_url
        window.open(res, logout_url)
        return logout_url
      }
      return null
    },

    async info() {
      const res: any = await AuthApi.info()
      const res_data = res || {}

      const keys = [
        'uid',
        'account',
        'name',
        'oid',
        'language',
        'exp',
        'time',
        'weight',
        'origin',
      ] as const

      keys.forEach((key) => {
        const dkey = key === 'uid' ? 'id' : key
        const value = res_data[dkey]
        if (key === 'exp' || key === 'time' || key === 'weight' || key === 'origin') {
          this[key] = Number(value)
        } else {
          this[key] = String(value)
        }
        wsCache.set('user.' + key, value)
      })

      this.setLanguage(this.language)
      this.platformInfo = wsCache.get('user.platformInfo')
    },
    setToken(token: string) {
      wsCache.set('user.token', token)
      this.token = token
    },
    setExp(exp: number) {
      wsCache.set('user.exp', exp)
      this.exp = exp
    },
    setTime(time: number) {
      wsCache.set('user.time', time)
      this.time = time
    },
    setUid(uid: string) {
      wsCache.set('user.uid', uid)
      this.uid = uid
    },
    setAccount(account: string) {
      wsCache.set('user.account', account)
      this.account = account
    },
    setName(name: string) {
      wsCache.set('user.name', name)
      this.name = name
    },
    setOid(oid: string) {
      wsCache.set('user.oid', oid)
      this.oid = oid
    },
    setLanguage(language: string) {
      if (!language) {
        language = 'zh-CN'
      } else if (language === 'zh_CN') {
        language = 'zh-CN'
      } else if (language === 'ko_KR') {
        language = 'ko-KR'
      }
      wsCache.set('user.language', language)
      this.language = language
      i18n.global.locale.value = language
      /* const { locale } = useI18n()
      locale.value = language */
      // locale.setLang(language)
    },
    setWeight(weight: number) {
      wsCache.set('user.weight', weight)
      this.weight = weight
    },
    setOrigin(origin: number) {
      wsCache.set('user.origin', origin)
      this.origin = origin
    },
    setPlatformInfo(info: any | null) {
      wsCache.set('user.platformInfo', info)
      this.platformInfo = info
    },
    clear() {
      const keys: string[] = [
        'token',
        'uid',
        'account',
        'name',
        'oid',
        'language',
        'exp',
        'time',
        'weight',
        'origin',
        'platformInfo',
      ]
      keys.forEach((key) => wsCache.delete('user.' + key))
      this.$reset()
    },
  },
})

export const useUserStore = () => {
  return UserStore(store)
}
