import { ElMessage } from 'element-plus-secondary'
import { useCache } from '@/utils/useCache'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useUserStore } from '@/stores/user'
import { request } from '@/utils/request'
import type { Router } from 'vue-router'
import { generateDynamicRouters } from './dynamic'
import { toLoginPage } from '@/utils/utils'

const appearanceStore = useAppearanceStoreWithOut()
const userStore = useUserStore()
const { wsCache } = useCache()
const whiteList = ['/login', '/admin-login']
const assistantWhiteList = ['/assistant', '/embeddedPage', '/embeddedCommon', '/401']
export const watchRouter = (router: Router) => {
  router.beforeEach(async (to: any, from: any, next: any) => {
    await loadXpackStatic()
    await appearanceStore.setAppearance()
    LicenseGenerator.generateRouters(router)
    if (to.path.startsWith('/login') && userStore.getUid) {
      next(to?.query?.redirect || '/')
      return
    }
    if (assistantWhiteList.includes(to.path)) {
      next()
      return
    }
    const token = wsCache.get('user.token')
    if (whiteList.includes(to.path)) {
      next()
      return
    }
    if (!token) {
      // ElMessage.error('Please login first')
      next(toLoginPage(to.fullPath))
      return
    }
    let isFirstDynamicPath = false
    if (!userStore.getUid) {
      await userStore.info()
      generateDynamicRouters(router)
      isFirstDynamicPath = to?.path && ['/ds/index', '/as/index'].includes(to.path)
      if (isFirstDynamicPath) {
        next({ ...to, replace: true })
        return
      }
    }
    if (to.path === '/' || accessCrossPermission(to)) {
      next('/chat')
      return
    }
    if (to.path === '/login' || to.path === '/admin-login') {
      console.info(from)
      next('/chat')
    } else {
      next()
    }
  })
}

const accessCrossPermission = (to: any) => {
  if (!to?.path) return false
  return (
    (to.path.startsWith('/system') && !userStore.isAdmin) ||
    (to.path.startsWith('/set') && !userStore.isSpaceAdmin)
  )
}
const loadXpackStatic = () => {
  if (document.getElementById('sqlbot_xpack_static')) {
    return Promise.resolve()
  }
  const url = `/xpack_static/license-generator.umd.js?t=${Date.now()}`
  return new Promise((resolve, reject) => {
    request
      .loadRemoteScript(url, 'sqlbot_xpack_static', () => {
        LicenseGenerator?.init(import.meta.env.VITE_API_BASE_URL).then(() => {
          resolve(true)
        })
      })
      .catch((error) => {
        console.error('Failed to load xpack_static script:', error)
        ElMessage.error('Failed to load license generator script')
        reject(error)
      })
  })
}
