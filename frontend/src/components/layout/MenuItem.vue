<script lang="ts">
import { h, defineComponent } from 'vue'
import { ElMenuItem, ElSubMenu, ElIcon } from 'element-plus-secondary'
import { useRouter, useRoute } from 'vue-router'
import chat from '@/assets/svg/menu/icon_chat_filled.svg'
import noChat from '@/assets/svg/menu/icon_chat_outlined.svg'
import dashboard from '@/assets/svg/menu/icon_dashboard_filled.svg'
import { useEmitt } from '@/utils/useEmitt'
import noDashboard from '@/assets/svg/menu/icon_dashboard_outlined.svg'
import ds from '@/assets/svg/menu/icon_database_filled.svg'
import noDs from '@/assets/svg/menu/icon_database_outlined.svg'
import model from '@/assets/svg/menu/icon_dataset_filled.svg'
import noModel from '@/assets/svg/menu/icon_dataset_outlined.svg'
import embedded from '@/assets/svg/menu/icon_embedded_filled.svg'
import noEmbedded from '@/assets/svg/menu/icon_embedded_outlined.svg'
import user from '@/assets/svg/menu/icon_member_filled.svg'
import noUser from '@/assets/svg/menu/icon_member_outlined.svg'
import workspace from '@/assets/svg/menu/icon_moments-categories_filled.svg'
import noWorkspace from '@/assets/svg/menu/icon_moments-categories_outlined.svg'
import set from '@/assets/svg/menu/icon_setting_filled.svg'
import noSet from '@/assets/svg/menu/icon-setting.svg'
import log from '@/assets/svg/menu/icon_log_filled.svg'
import noLog from '@/assets/svg/menu/icon_log_outlined.svg'

const iconMap = {
  chat,
  noChat,
  ds,
  noDs,
  dashboard,
  noDashboard,
  workspace,
  noWorkspace,
  set,
  noSet,
  user,
  noUser,
  model,
  noModel,
  embedded,
  noEmbedded,
  log,
  noLog,
} as { [key: string]: any }

const MenuItem = defineComponent({
  name: 'MenuItem',
  props: {
    menu: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const router = useRouter()
    const route = useRoute()
    const titleWithIcon = (props: any) => {
      const { title, icon } = props
      return [
        h(ElIcon, { size: '18' }, { default: () => h(iconMap[icon]) }),
        h('span', null, { default: () => title }),
      ]
    }

    const handleMenuClick = (e: any) => {
      if (e.index === '/ds/index') {
        useEmitt().emitter.emit('ds-index-click')
      }
      if (e.index) {
        router.push(e.redirect || e.index)
      }
    }

    return () => {
      const { children, hidden, path } = props.menu
      if (hidden) {
        return null
      }

      if (children?.length) {
        const { title, iconDeActive, iconActive } = props.menu?.meta || {}
        const icon = route.path.startsWith(path) ? iconActive : iconDeActive
        return h(
          ElSubMenu,
          { index: path, onClick: () => handleMenuClick(props.menu) },
          {
            title: () => titleWithIcon({ title, icon }),
            default: () => [
              h(MenuItem, { menu: { meta: { title } }, class: 'subTitleMenu' }),
              children.map((ele: any) => h(MenuItem, { menu: ele })),
            ],
          }
        )
      }

      const { title, iconDeActive, iconActive } = props.menu?.meta || {}
      const icon = route.path === path ? iconActive : iconDeActive
      const iconCom: any = iconMap[icon] ? ElIcon : null
      return h(
        ElMenuItem,
        { index: path, onClick: (e: any) => handleMenuClick(e) },
        {
          default: () => [
            h(
              iconCom,
              { size: 18 },
              {
                default: () => h(iconMap[icon]),
              }
            ),
            h('span', null, { default: () => title }),
          ],
        }
      )
    }
  },
})
/* const MenuItem = (props: any) => {
const MenuItem = (props: any) => {
  const router = useRouter()

  const { children, hidden, path } = props.menu
  if (hidden) {
    return null
  }
  if (children?.length) {
    return h(
      ElSubMenu,
      { index: path, onClick: (e: any) => handleMenuClick(e) },
      {
        index: path,
      },
      {
        title: () => titleWithIcon(props),
        default: () => children.map((ele: any) => h(MenuItem, { menu: ele })),
      }
    )
  }
  const { title, icon } = props.menu?.meta || {}
  const iconCom: any = iconMap[icon] ? ElIcon : null
  return h(
    ElMenuItem,
    { index: path, onClick: (e: any) => handleMenuClick(e) },
    {
      index: path,
      onClick: () => {
        router.push(path)
      },
    },
    {
      title: h('span', null, { default: () => title }),
      default: h(iconCom, null, {
        default: () => h(iconMap[icon]),
      }),
    }
  )
} */
export default MenuItem
</script>
