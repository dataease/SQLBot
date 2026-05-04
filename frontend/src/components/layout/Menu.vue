<script lang="ts" setup>
import { computed } from 'vue'
import { ElMenu } from 'element-plus-secondary'
import { useRoute, useRouter } from 'vue-router'
import MenuItem from './MenuItem.vue'
import { useUserStore } from '@/stores/user'
// import { routes } from '@/router'
const userStore = useUserStore()
const router = useRouter()
defineProps({
  collapse: Boolean,
})

const route = useRoute()
// const menuList = computed(() => route.matched[0]?.children || [])
const activeMenu = computed(() => route.path)
/* const activeIndex = computed(() => {
  const arr = route.path.split('/')
  return arr[arr.length - 1]
}) */
const showSysmenu = computed(() => {
  return route.path.includes('/system')
})

const formatRoute = (arr: any, parentPath = '') => {
  return arr.map((element: any) => {
    let children: any = []
    const path = `${parentPath ? parentPath + '/' : ''}${element.path}`
    if (element.children?.length) {
      children = formatRoute(element.children, path)
    }
    return {
      ...element,
      path,
      children,
    }
  })
}

const routerList = computed(() => {
  if (showSysmenu.value) {
    const [sysRouter] = formatRoute(
      router.getRoutes().filter((route: any) => route?.name === 'system')
    )
    return sysRouter.children
  }
  const list = router.getRoutes().filter((route) => {
    return (
      !route.path.includes('embeddedPage') &&
      !route.path.includes('assistant') &&
      !route.path.includes('embeddedPage') &&
      !route.path.includes('canvas') &&
      !route.path.includes('member') &&
      !route.path.includes('professional') &&
      !route.path.includes('401') &&
      !route.path.includes('training') &&
      !route.path.includes('prompt') &&
      !route.path.includes('permission') &&
      !route.path.includes('embeddedCommon') &&
      !route.path.includes('preview') &&
      !route.path.includes('audit') &&
      route.path !== '/login' &&
      route.path !== '/admin-login' &&
      route.path !== '/chatPreview' &&
      !route.path.includes('/system') &&
      ((route.path.includes('set') && userStore.isSpaceAdmin) || !route.redirect) &&
      route.path !== '/:pathMatch(.*)*' &&
      !route.path.includes('dsTable')
    )
  })

  return list
})
</script>

<template>
  <el-menu :default-active="activeMenu" class="el-menu-demo ed-menu-vertical" :collapse="collapse">
    <MenuItem v-for="menu in routerList" :key="menu.path" :menu="menu"></MenuItem>
  </el-menu>
</template>

<style lang="less">
.ed-menu-vertical {
  --ed-menu-item-height: 40px;
  --ed-menu-bg-color: transparent;
  --ed-menu-base-level-padding: 4px;
  border-right: none;
  .ed-menu-item {
    height: 40px !important;
    border-radius: 8px !important;
    margin-bottom: 2px;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: -0.224px;
    color: var(--color-muted);
    &.is-active {
      background-color: rgba(0, 102, 204, 0.1) !important;
      border-radius: 8px;
      font-weight: 600;
      color: var(--color-ink);
    }
  }

  .ed-sub-menu .ed-sub-menu__title {
    border-radius: 8px;
    color: var(--color-muted);
    font-size: 14px;
    font-weight: 400;
    letter-spacing: -0.224px;
  }

  .ed-sub-menu.is-active:not(.is-opened) {
    .ed-sub-menu__title {
      background-color: rgba(0, 102, 204, 0.1) !important;
      color: #0066cc !important;
      font-weight: 600;
    }
  }

  .ed-sub-menu.is-active.is-opened {
    .ed-sub-menu__title {
      color: #0066cc !important;
      font-weight: 600;
    }
  }

  .ed-sub-menu .ed-icon {
    margin-right: 8px;
    color: var(--color-muted);
  }
}
.ed-popper.is-light:has(.ed-menu--popup) {
  border: 1px solid var(--color-hairline);
  border-radius: 8px;
  box-shadow: none;
  background: var(--color-canvas);
  overflow: hidden;
}
.ed-menu--popup {
  padding: 8px;
  background: var(--color-canvas);

  .ed-menu-item {
    padding: 9px 16px;
    height: 40px !important;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: -0.224px;
    color: var(--color-muted);
    &.is-active {
      background-color: rgba(0, 102, 204, 0.1) !important;
      font-weight: 600;
      color: var(--color-ink);
    }
  }
}

/* 问数侧栏折叠时，设置等子菜单浮层需盖过下方历史区与主内容区 */
.menu-left-sub-popup {
  z-index: 6000 !important;
}
.ed-sub-menu {
  .subTitleMenu {
    display: none;
  }
}

.ed-menu--popup-container .subTitleMenu {
  color: var(--color-muted) !important;
  pointer-events: none;
}
</style>
