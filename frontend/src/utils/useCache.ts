import WebStorageCache from 'web-storage-cache'

type CacheType = 'localStorage' | 'sessionStorage'

const getPathPrefix = () => {
  const pathname = window.location.pathname
  // eslint-disable-next-line no-useless-escape
  const match = pathname.match(/^\/([^\/]+)/)
  return match ? `${match[1]}_` : 'sqlbot_v1_'
}

export const useCache = (type: CacheType = 'localStorage') => {
  const originalCache = new WebStorageCache({ storage: type })
  const prefix = getPathPrefix()

  const methodsNeedKeyPrefix = new Set(['get', 'delete', 'touch', 'add', 'replace'])

  const wrappedCache = new Proxy(originalCache, {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    get(target, prop, _receiver) {
      const originalMethod = target[prop as keyof typeof target]

      if (typeof originalMethod !== 'function') {
        return originalMethod
      }

      if (methodsNeedKeyPrefix.has(prop as string)) {
        return function (this: any, key: string, ...args: any[]) {
          // 自动加上前缀
          const scopedKey = `${prefix}${key}`
          return (originalMethod as (...args: any[]) => any).apply(target, [scopedKey, ...args])
        }
      }

      if (prop === 'set') {
        return function (this: any, key: string, value: any, ...args: any[]) {
          const scopedKey = `${prefix}${key}`
          // eslint-disable-next-line @typescript-eslint/no-unsafe-function-type
          return (originalMethod as Function).apply(target, [scopedKey, value, ...args])
        }
      }

      return originalMethod.bind(target)
    },
  })

  return {
    wsCache: wrappedCache,
  }
}
