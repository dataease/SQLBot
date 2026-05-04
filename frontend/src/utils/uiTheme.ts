import { setCurrentColor } from '@/utils/utils'

export const UI_THEME_STORAGE_KEY = 'sqlbot-ui-theme'
export const FAVICON_THEMED_FLAG = 'sqlbot-favicon-themed'

export type UiThemeId = 'claude' | 'apple' | 'notion' | 'airbnb'

export const UI_THEME_ORDER: UiThemeId[] = ['claude', 'apple', 'notion', 'airbnb']

/** Primary accent per DESIGN_*.md — keeps Element components in lock-step with CSS tokens. */
const THEME_PRIMARY_HEX: Record<UiThemeId, string> = {
  claude: '#cc785c', // Coral (DESIGN_CLAUDE.md)
  apple: '#0066cc', // Action Blue (DESIGN_APPLE.md)
  notion: '#7c66dc', // Notion Purple (DESIGN_NOTION.md)
  airbnb: '#ff385c', // Rausch (DESIGN_AIRBNB.md)
}

export function isUiThemeId(v: string | null | undefined): v is UiThemeId {
  return v === 'claude' || v === 'apple' || v === 'notion' || v === 'airbnb'
}

export function getThemePrimaryHex(id: UiThemeId): string {
  return THEME_PRIMARY_HEX[id]
}

export function getStoredUiTheme(): UiThemeId {
  try {
    const raw = localStorage.getItem(UI_THEME_STORAGE_KEY)
    if (isUiThemeId(raw)) return raw
  } catch {
    /* ignore */
  }
  return 'claude'
}

/** Build a data: URL favicon tinted with the given hex color. Mirrors logo-custom_small.svg geometry. */
function buildThemedFaviconDataUrl(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 30 30" fill="${color}"><path d="M28.3328 13.6689h-.2309c.1379.7582.2069 1.5272.2064 2.2977.0049.9464-.1078 1.8897-.3354 2.8083h.6507c.2785 0 .5455-.1106.7425-.3075.1969-.197.3075-.464.3075-.7425V15.01c0-.176-.0347-.3504-.102-.5131a1.34 1.34 0 0 0-.2907-.4351 1.34 1.34 0 0 0-.4351-.2907 1.34 1.34 0 0 0-.5131-.1021Z"/><path d="M1.6916 15.9666c-.0005-.7705.0686-1.5395.2064-2.2977h-.2308c-.3556.0001-.6967.1413-.9482.3928a1.341 1.341 0 0 0-.3928.9482V17.725c0 .2784.1107.5454.3075.7424.197.197.464.3076.7425.3076h.6507c-.2277-.9186-.3404-1.862-.3354-2.8084Z"/><path d="M15 3.795C8.111 3.795 2.526 9.077 2.526 15.966c0 6.89 5.585 10.239 12.474 10.239 6.889 0 12.474-3.349 12.474-10.238C27.474 9.078 21.889 3.795 15 3.795Zm3.027 17.33H11.974c-.857.001-1.704-.181-2.484-.535-.564-.256-2.208.282-2.663-.127-.551-.495.117-1.969-.221-2.636-.427-.842-.648-1.773-.647-2.716 0-1.595.634-3.125 1.762-4.253s2.658-1.761 4.253-1.761h6.053c1.595 0 3.125.633 4.253 1.761 1.128 1.128 1.762 2.658 1.762 4.253 0 .79-.156 1.572-.458 2.302a6.012 6.012 0 0 1-1.304 1.951 6.012 6.012 0 0 1-1.951 1.304 6.012 6.012 0 0 1-2.302.458Z"/><path d="M10.546 14.915H8.766v3.88h1.78v-3.88ZM14.12 13.193h-1.78v5.602h1.78v-5.602ZM17.694 15.438h-1.78v3.357h1.78v-3.357ZM21.233 12.452h-1.779v6.343h1.779v-6.343Z"/></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

/** Update <link rel="icon"> with a themed favicon. Skipped if a non-themed icon was set externally. */
export function applyThemedFavicon(color: string) {
  const link = document.querySelector('link[rel="icon"]') as HTMLLinkElement | null
  if (!link) return
  if (link.dataset.themed === undefined && link.getAttribute('href')) {
    /* If a server-uploaded favicon already exists (no themed flag), keep it */
    const href = link.getAttribute('href') || ''
    if (href && !href.startsWith('data:') && !href.endsWith('LOGO-fold.svg')) return
  }
  link.setAttribute('href', buildThemedFaviconDataUrl(color))
  link.setAttribute('type', 'image/svg+xml')
  link.dataset.themed = 'true'
}

/** Sets data-ui-theme, localStorage, primary color variables, and favicon. */
export function applyUiTheme(id: UiThemeId) {
  try {
    localStorage.setItem(UI_THEME_STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
  document.documentElement.setAttribute('data-ui-theme', id)
  setCurrentColor(THEME_PRIMARY_HEX[id])
  applyThemedFavicon(THEME_PRIMARY_HEX[id])
}

/** Call after appearance API sets server theme so user UI preset wins */
export function reapplyUiThemePrimary() {
  applyUiTheme(getStoredUiTheme())
}

export function initUiThemeFromStorage() {
  const id = getStoredUiTheme()
  document.documentElement.setAttribute('data-ui-theme', id)
  setCurrentColor(THEME_PRIMARY_HEX[id])
  applyThemedFavicon(THEME_PRIMARY_HEX[id])
}
