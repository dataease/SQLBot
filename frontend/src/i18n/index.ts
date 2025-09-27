import { createI18n } from 'vue-i18n'
import en from './en.json'
import zhCN from './zh-CN.json'
import koKR from './ko-KR.json'
import elementEnLocale from 'element-plus-secondary/es/locale/lang/en'
import elementZhLocale from 'element-plus-secondary/es/locale/lang/zh-cn'
import { useCache } from '@/utils/useCache'

const elementKoLocale = elementEnLocale
const { wsCache } = useCache()

const getDefaultLocale = () => {
  const language = wsCache.get('user.language')
  return language || 'zh-CN'
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
  'ko-KR': {
    ...koKR,
    el: elementKoLocale,
  },
}

export const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  globalInjection: true,
  messages,
})

const elementLocales = {
  en: elementEnLocale,
  'zh-CN': elementZhLocale,
  'ko-KR': elementKoLocale,
} as const

export const getElementLocale = () => {
  const locale = i18n.global.locale.value as keyof typeof elementLocales
  return elementLocales[locale] ?? elementEnLocale
}