import { defineStore } from 'pinia'
import { store } from '@/stores/index.ts'
import { request } from '@/utils/request.ts'
import { formatArg } from '@/utils/utils.ts'

interface ChatConfig {
  sqlbot_name: string
  expand_thinking_block: boolean
  limit_rows: boolean
  show_sql: boolean
  show_log: boolean
}

export const chatConfigStore = defineStore('chatConfigStore', {
  state: (): ChatConfig => {
    return {
      sqlbot_name: 'SQLBot',
      expand_thinking_block: false,
      limit_rows: true,
      show_sql: true,
      show_log: true,
    }
  },
  getters: {
    getSQLBotName(): string {
      return this.sqlbot_name
    },
    getExpandThinkingBlock(): boolean {
      return this.expand_thinking_block
    },
    getShowSQL(): boolean {
      return this.show_sql
    },
    getShowLog(): boolean {
      return this.show_log
    },
    getLimitRows(): boolean {
      return this.limit_rows
    },
  },
  actions: {
    fetchGlobalConfig() {
      request.get('/system/parameter/chat').then((res: any) => {
        if (res) {
          res.forEach((item: any) => {
            if (item.pkey === 'chat.expand_thinking_block') {
              this.expand_thinking_block = formatArg(item.pval)
            }
            if (item.pkey === 'chat.show_sql') {
              this.show_sql = formatArg(item.pval)
            }
            if (item.pkey === 'chat.show_log') {
              this.show_log = formatArg(item.pval)
            }
            if (item.pkey === 'chat.limit_rows') {
              this.limit_rows = formatArg(item.pval)
            }
            if (item.pkey === 'chat.sqlbot_name') {
              if (item.pval && item.pval.trim().length > 0) {
                this.sqlbot_name = item.pval
              }
            }
          })
        }
      })
    },
  },
})

export const useChatConfigStore = () => {
  return chatConfigStore(store)
}
