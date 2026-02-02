import logo_dingtalk from '@/assets/svg/logo_dingtalk.svg'
import logo_lark from '@/assets/svg/logo_lark.svg'
import logo_wechatWork from '@/assets/svg/logo_wechat-work.svg'
export interface SettingRecord {
  pkey: string
  pval: string
  type: string
  sort: number
}

export interface ToolTipRecord {
  key: string
  val: string
}

export interface PlatformCard {
  id?: number
  type: number
  name: string
  config: object
  enable: boolean
  valid: boolean
}

export const settingMapping = {
  6: [
    {
      realKey: 'corpid',
      pkey: 'CorpId',
      pval: '',
      type: 'text',
      sort: 1,
    },
    {
      realKey: 'agent_id',
      pkey: 'AgentId',
      pval: '',
      type: 'text',
      sort: 2,
    },
    {
      realKey: 'corpsecret',
      pkey: 'APP Secret',
      pval: '',
      type: 'pwd',
      sort: 3,
    },
  ],
  7: [
    {
      realKey: 'corpid',
      pkey: 'CorpId',
      pval: '',
      type: 'text',
      sort: 1,
    },
    {
      realKey: 'agent_id',
      pkey: 'agentId',
      pval: '',
      type: 'text',
      sort: 2,
    },
    {
      realKey: 'client_id',
      pkey: 'APP Key',
      pval: '',
      type: 'text',
      sort: 3,
    },
    {
      realKey: 'client_secret',
      pkey: 'APP Secret',
      pval: '',
      type: 'pwd',
      sort: 4,
    },
  ],
  8: [
    {
      realKey: 'client_id',
      pkey: 'APP Key',
      pval: '',
      type: 'text',
      sort: 1,
    },
    {
      realKey: 'client_secret',
      pkey: 'APP Secret',
      pval: '',
      type: 'pwd',
      sort: 2,
    },
  ],
  9: [
    {
      realKey: 'client_id',
      pkey: 'APP Key',
      pval: '',
      type: 'text',
      sort: 1,
    },
    {
      realKey: 'client_secret',
      pkey: 'APP Secret',
      pval: '',
      type: 'pwd',
      sort: 2,
    },
  ],
} as any

export const cardMapping = {
  6: {
    title: 'user.wecom',
    icon: logo_wechatWork,
    settingList: settingMapping[6],
    copyField: ['CorpId', 'APP Secret'],
  },
  7: {
    title: 'user.dingtalk',
    icon: logo_dingtalk,
    settingList: settingMapping[7],
    copyField: ['CorpId', 'APP Secret'],
  },
  8: {
    title: 'user.lark',
    icon: logo_lark,
    settingList: settingMapping[8],
    copyField: ['APP Key', 'APP Secret'],
  },
  9: {
    title: 'user.larksuite',
    icon: logo_lark,
    settingList: settingMapping[9],
    copyField: ['APP Key', 'APP Secret'],
  },
} as any

export const getPlatformCardConfig = (origin: number) => {
  return cardMapping[origin]
}
