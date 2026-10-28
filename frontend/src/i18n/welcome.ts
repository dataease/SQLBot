import en from './en.json'
import zhCN from './zh-CN.json'
import zhTW from './zh-TW.json'
import koKR from './ko-KR.json'
import thTH from './th-TH.json'

type WelcomeKey =
  | 'embedded.i_am_sqlbot'
  | 'embedded.data_analysis_now'
  | 'qa.hint_description'
  | 'common.intelligent_questioning_platform'

const messages = [en, zhCN, zhTW, koKR, thTH]
const defaultTitles = new Set(messages.map((message) => message.embedded.i_am_sqlbot))
const defaultDescriptions = new Set(
  messages.flatMap((message) => [message.embedded.data_analysis_now, message.qa.hint_description])
)
const defaultSlogans = new Set(
  messages.map((message) => message.common.intelligent_questioning_platform)
)
const defaultsByKey: Record<WelcomeKey, Set<string>> = {
  'embedded.i_am_sqlbot': defaultTitles,
  'embedded.data_analysis_now': defaultDescriptions,
  'qa.hint_description': defaultDescriptions,
  'common.intelligent_questioning_platform': defaultSlogans,
}

// An empty string means "follow the display language" in both existing save APIs.
// Older editors persisted translated defaults. Match only exact stock strings;
// never trim, translate or otherwise rewrite a user's custom text.
export function normalizeWelcome(value: string | null | undefined, key: WelcomeKey): string {
  const defaults = defaultsByKey[key]
  return value == null || defaults.has(value) ? '' : value
}

export function resolveWelcome(
  value: string | null | undefined,
  key: WelcomeKey,
  translate: (key: WelcomeKey) => string
): string {
  return normalizeWelcome(value, key) || translate(key)
}
