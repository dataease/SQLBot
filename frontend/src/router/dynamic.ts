import LayoutDsl from '@/components/layout/LayoutDsl.vue'

import Datasource from '@/views/ds/Datasource.vue'
import SetAssistant from '@/views/system/embedded/iframe.vue'
import { i18n } from '@/i18n'
import { useUserStore } from '@/stores/user'
import type { Router } from 'vue-router'
const userStore = useUserStore()
const t = i18n.global.t

const dynamicRouterList = [
  {
    path: '/ds',
    component: LayoutDsl,
    name: 'ds-menu',
    redirect: '/ds/index',
    children: [
      {
        path: 'index',
        name: 'ds',
        component: Datasource,
        meta: { title: t('menu.Data Connections'), iconActive: 'ds', iconDeActive: 'noDs' },
      },
    ],
  },
  {
    path: '/as',
    component: LayoutDsl,
    name: 'as-menu',
    redirect: '/as/index',
    children: [
      {
        path: 'index',
        name: 'as',
        component: SetAssistant,
        meta: {
          title: t('embedded.assistant_app'),
          iconActive: 'embedded',
          iconDeActive: 'noEmbedded',
        },
      },
    ],
    meta: { title: t('embedded.assistant_app') },
  },
] as any[]

const reduceRouters = (router: Router, invalid_router_name_list: string[]) => {
  const tree = router.getRoutes()
  const invalid_name_set = [] as any
  invalid_router_name_list.forEach((router_name: string) => {
    router.removeRoute(router_name)
    invalid_name_set.push(router_name)
  })

  const pathsSet = new Set(invalid_router_name_list)

  function processNode(node: any): boolean {
    if (node.name && pathsSet.has(node.name)) {
      return true
    }
    if (node.children) {
      const newChildren: any[] = []

      for (const child of node.children) {
        const shouldRemove = processNode(child)
        if (!shouldRemove) {
          newChildren.push(child)
        }
      }

      if (newChildren.length > 0) {
        node.children = newChildren
        return false
      } else {
        node.children = undefined
      }
    }

    return false
  }

  let i = 0
  while (i < tree.length) {
    if (processNode(tree[i])) {
      tree.splice(i, 1)
    } else {
      i++
    }
  }
}

export const generateDynamicRouters = (router: Router) => {
  if (userStore.isAdmin || userStore.isSpaceAdmin) {
    dynamicRouterList.forEach((item: any) => {
      if (!item.parent) {
        router.addRoute(item)
      } else {
        router.addRoute(item.parent, item)
        const parentRoute: any = router.getRoutes().find((r: any) => r.name === item.parent)
        if (parentRoute?.children) {
          parentRoute.children.push(item)
        }
      }
    })
  } else {
    const router_name_list = [] as string[]
    const stack = [...dynamicRouterList]
    while (stack.length) {
      const item = stack.pop()
      if (item.name) {
        router_name_list.push(item.name)
      }
      if (item.children?.length) {
        item.children.forEach((child: any) => {
          stack.push(child)
        })
      }
    }
    reduceRouters(router, router_name_list)
  }
}
