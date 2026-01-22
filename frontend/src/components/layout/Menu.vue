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
    border-radius: 6px !important;
    margin-bottom: 2px;
    &.is-active {
      background-color: #fff !important;
      border-radius: 6px;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-sub-menu__title {
    border-radius: 6px;
  }

  .ed-sub-menu.is-active:not(.is-opened) {
    .ed-sub-menu__title {
      background-color: #fff !important;
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu.is-active.is-opened {
    .ed-sub-menu__title {
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-icon {
    margin-right: 8px;
  }
}
.ed-popper.is-light:has(.ed-menu--popup) {
  border: 1px solid #dee0e3;
  border-radius: 6px;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  background: #eff1f0;
  overflow: hidden;
}
.ed-menu--popup {
  padding: 8px;
  background: #eff1f0;

  .ed-menu-item {
    padding: 9px 16px;
    height: 40px !important;
    border-radius: 6px;
    &.is-active {
      background-color: #fff !important;
      font-weight: 500;
    }
  }
}
.ed-sub-menu {
  .subTitleMenu {
    display: none;
  }
}

.ed-menu--popup-container .subTitleMenu {
  color: #646a73 !important;
  pointer-events: none;
}
</style>
