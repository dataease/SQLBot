import { createRouter, createWebHashHistory } from 'vue-router'
// @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
import Layout from '@/components/layout/index.vue'
import LayoutDsl from '@/components/layout/LayoutDsl.vue'
import SinglePage from '@/components/layout/SinglePage.vue'
import login from '@/views/login/index.vue'
import chat from '@/views/chat/index.vue'
import Datasource from '@/views/ds/Datasource.vue'
import DashboardEditor from '@/views/dashboard/editor/index.vue'
import DashboardPreview from '@//views/dashboard/preview/SQPreviewSingle.vue'
import Dashboard from '@/views/dashboard/index.vue'
import Model from '@/views/system/model/Model.vue'
import Embedded from '@/views/system/embedded/index.vue'
import assistantTest from '@/views/system/embedded/Test.vue'
import assistant from '@/views/embedded/index.vue'
import EmbeddedPage from '@/views/embedded/page.vue'
import Member from '@/views/system/member/index.vue'
import Professional from '@/views/system/professional/index.vue'
import Training from '@/views/system/training/index.vue'
import Prompt from '@/views/system/prompt/index.vue'
import Appearance from '@/views/system/appearance/index.vue'
import Permission from '@/views/system/permission/index.vue'
import User from '@/views/system/user/User.vue'
import Workspace from '@/views/system/workspace/index.vue'
import Page401 from '@/views/error/index.vue'
import { i18n } from '@/i18n'
import { watchRouter } from './watch'

const t = i18n.global.t
export const routes = [
  {
    path: '/login',
    name: 'login',
    component: login,
  },
  {
    path: '/chat',
    component: LayoutDsl,
    redirect: '/chat/index',
    children: [
      {
        path: 'index',
        name: 'chat',
        component: chat,
        props: (route: any) => {
          return { startChatDsId: route.query.start_chat }
        },
        meta: { title: t('menu.Data Q&A'), iconActive: 'chat', iconDeActive: 'noChat' },
      },
    ],
  },
  {
    path: '/dsTable',
    component: SinglePage,
    children: [
      {
        path: ':dsId/:dsName',
        name: 'dsTable',
        component: () => import('@/views/ds/TableList.vue'),
        props: true,
      },
    ],
  },
  {
    path: '/ds',
    component: LayoutDsl,
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
    path: '/dashboard',
    component: LayoutDsl,
    redirect: '/dashboard/index',
    children: [
      {
        path: 'index',
        name: 'dashboard',
        component: Dashboard,
        meta: {
          title: t('dashboard.dashboard'),
          iconActive: 'dashboard',
          iconDeActive: 'noDashboard',
        },
      },
    ],
  },
  {
    path: '/set',
    component: LayoutDsl,
    redirect: '/set/member',
    meta: { title: t('workspace.set'), iconActive: 'set', iconDeActive: 'noSet' },
    children: [
      {
        path: '/set/member',
        name: 'member',
        component: Member,
        meta: { title: t('workspace.member_management') },
      },
      {
        path: '/set/permission',
        name: 'permission',
        component: Permission,
        meta: { title: t('workspace.permission_configuration') },
      },
      {
        path: '/set/professional',
        name: 'professional',
        component: Professional,
        meta: { title: t('professional.professional_terminology') },
      },
      {
        path: '/set/training',
        name: 'training',
        component: Training,
        meta: { title: t('training.data_training') },
      },
      {
        path: '/set/prompt',
        name: 'prompt',
        component: Prompt,
        meta: { title: t('prompt.customize_prompt_words') },
      },
    ],
  },
  {
    path: '/canvas',
    name: 'canvas',
    component: DashboardEditor,
    meta: { title: 'canvas', icon: 'dashboard' },
  },
  {
    path: '/dashboard-preview',
    name: 'preview',
    component: DashboardPreview,
    meta: { title: 'DashboardPreview', icon: 'dashboard' },
  },
  {
    path: '/system',
    component: LayoutDsl,
    redirect: '/system/user',
    meta: { hidden: true },
    children: [
      {
        path: 'user',
        name: 'user',
        component: User,
        meta: { title: t('user.user_management'), iconActive: 'user', iconDeActive: 'noUser' },
      },
      {
        path: 'workspace',
        name: 'workspace',
        component: Workspace,
        meta: {
          title: t('user.workspace'),
          iconActive: 'workspace',
          iconDeActive: 'noWorkspace',
        },
      },
      {
        path: 'model',
        name: 'model',
        component: Model,
        meta: {
          title: t('model.ai_model_configuration'),
          iconActive: 'model',
          iconDeActive: 'noModel',
        },
      },
      {
        path: 'embedded',
        name: 'embedded',
        component: Embedded,
        meta: {
          title: t('embedded.embedded_management'),
          iconActive: 'embedded',
          iconDeActive: 'noEmbedded',
        },
      },
      {
        path: 'setting',
        meta: { title: t('system.system_settings'), iconActive: 'set', iconDeActive: 'noSet' },
        redirect: 'system_/appearance',
        name: 'setting',
        children: [
          {
            path: 'appearance',
            name: 'appearance',
            component: Appearance,
            meta: { title: t('system.appearance_settings') },
          },
        ],
      },
    ],
  },

  {
    path: '/assistant',
    name: 'assistant',
    component: assistant,
  },
  {
    path: '/embeddedPage',
    name: 'embeddedPage',
    component: EmbeddedPage,
  },
  {
    path: '/assistantTest',
    name: 'assistantTest',
    component: assistantTest,
  },
  {
    path: '/401',
    name: '401',
    hidden: true,
    meta: {},
    component: Page401,
  },
]
const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
watchRouter(router)
export default router
