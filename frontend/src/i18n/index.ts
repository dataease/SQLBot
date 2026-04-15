import { createI18n } from 'vue-i18n'
import en from './en.json'
import zhCN from './zh-CN.json'
import zhTw from './zh-TW.json'
import koKR from './ko-KR.json'
import elementEnLocale from 'element-plus-secondary/es/locale/lang/en'
import elementZhLocale from 'element-plus-secondary/es/locale/lang/zh-cn'
import elementTwLocale from 'element-plus-secondary/es/locale/lang/zh-tw'
import { useCache } from '@/utils/useCache'
import { getBrowserLocale } from '@/utils/utils'

const elementKoLocale = elementEnLocale
const { wsCache } = useCache()

const getDefaultLocale = () => {
  return wsCache.get('user.language') || getBrowserLocale() || 'zh-CN'
}

const messages = {
  en: {
    ...en,
    el: elementEnLocale,
  },
  'zh-CN': {
    ...zhCN,
    el: elementZhLocale,
  },
  'zh-TW': {
    ...zhTw,
    el: elementTwLocale,
  },
  'ko-KR': {
    ...koKR,
    el: elementKoLocale,
  },
}

export const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'zh-CN',
  globalInjection: true,
  messages,
})

const elementLocales = {
  en: elementEnLocale,
  'zh-CN': elementZhLocale,
  'zh-TW': elementTwLocale,
  'ko-KR': elementKoLocale,
} as const

export const getElementLocale = () => {
  const locale = i18n.global.locale.value as keyof typeof elementLocales
  return elementLocales[locale] ?? elementEnLocale
}
