import { useI18n } from 'vue-i18n'
import type { RouteMeta } from 'vue-router'

export const useMenuTitle = () => {
  const { t } = useI18n()
  return (meta: RouteMeta = {}): string => {
    if (typeof meta.titleKey === 'string') {
      return t(meta.titleKey)
    }
    // Extension routes may supply an already formatted title.
    return typeof meta.title === 'string' ? meta.title : ''
  }
}
