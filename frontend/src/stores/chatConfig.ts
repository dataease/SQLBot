import { defineStore } from 'pinia'
import { store } from '@/stores/index.ts'
import { request } from '@/utils/request.ts'
import { formatArg } from '@/utils/utils.ts'

interface ChatConfig {
  expand_thinking_block: boolean
  limit_rows: boolean
}

export const chatConfigStore = defineStore('chatConfigStore', {
  state: (): ChatConfig => {
    return {
      expand_thinking_block: false,
      limit_rows: true,
    }
  },
  getters: {
    getExpandThinkingBlock(): boolean {
      return this.expand_thinking_block
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
            if (item.pkey === 'chat.limit_rows') {
              this.limit_rows = formatArg(item.pval)
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
