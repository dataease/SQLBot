import { defineStore } from 'pinia'
import { store } from './index'
import { chatApi, ChatInfo } from '@/api/chat'
import { useCache } from '@/utils/useCache'

const { wsCache } = useCache()
const flagKey = 'sqlbit-assistant-flag'
type Resolver<T = any> = (value: T | PromiseLike<T>) => void
type Rejecter = (reason?: any) => void
interface PendingRequest<T = any> {
  resolve: Resolver<T>
  reject: Rejecter
}
interface AssistantState {
  id: string
  token: string
  assistant: boolean
  flag: number
  type: number
  certificate: string
  online: boolean
  pageEmbedded?: boolean
  history: boolean
  hostOrigin: string
  autoDs?: boolean
  requestPromiseMap: Map<string, PendingRequest>
}

export const AssistantStore = defineStore('assistant', {
  state: (): AssistantState => {
    return {
      id: '',
      token: '',
      assistant: false,
      flag: 0,
      type: 0,
      certificate: '',
      online: false,
      pageEmbedded: false,
      history: true,
      hostOrigin: '',
      autoDs: false,
      requestPromiseMap: new Map<string, PendingRequest>(),
    }
  },
  getters: {
    getCertificate(): string {
      return this.certificate
    },
    getId(): string {
      return this.id
    },
    getToken(): string {
      return this.token
    },
    getAssistant(): boolean {
      return this.assistant
    },
    getFlag(): number {
      return this.flag
    },
    getType(): number {
      return this.type
    },
    getOnline(): boolean {
      return this.online
    },
    getHistory(): boolean {
      return this.history
    },
    getPageEmbedded(): boolean {
      return this.pageEmbedded || false
    },
    getEmbedded(): boolean {
      return this.assistant && this.type === 4
    },
    getHostOrigin(): string {
      return this.hostOrigin
    },
    getAutoDs(): boolean {
      return !!this.autoDs
    },
  },
  actions: {
    refreshCertificate<T>() {
      const timeout = 30000
      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          this.requestPromiseMap.delete(this.id)
          reject(new Error(`Request ${this.id} timed out after ${timeout}ms`))
        }, timeout)
        this.requestPromiseMap.set(this.id, {
          resolve: (value: T) => {
            clearTimeout(timeoutId)
            this.requestPromiseMap.delete(this.id)
            resolve(value)
          },
          reject: (reason) => {
            clearTimeout(timeoutId)
            this.requestPromiseMap.delete(this.id)
            reject(reason)
          },
        })
        const readyData = {
          eventName: this.pageEmbedded ? 'sqlbot_embedded_event' : 'sqlbot_assistant_event',
          busi: 'ready',
          ready: true,
          messageId: this.id,
        }
        window.parent.postMessage(readyData, '*')
      })
    },
    resolveCertificate(data?: any) {
      const peddingRequest = this.requestPromiseMap.get(this.id)
      if (peddingRequest) {
        peddingRequest.resolve(data)
      }
    },
    setId(id: string) {
      this.id = id
    },
    setCertificate(certificate: string) {
      this.certificate = certificate
    },
    setType(type: number) {
      this.type = type
    },
    setToken(token: string) {
      this.token = token
    },
    setAssistant(assistant: boolean) {
      this.assistant = assistant
    },
    setFlag(flag: number) {
      if (wsCache.get(flagKey)) {
        this.flag = wsCache.get(flagKey)
      } else {
        this.flag = flag
        wsCache.set(flagKey, flag)
      }
    },
    setPageEmbedded(embedded?: boolean) {
      this.pageEmbedded = !!embedded
    },
    setOnline(online: boolean) {
      this.online = !!online
    },
    setHistory(history: boolean) {
      this.history = history ?? true
    },
    setHostOrigin(origin: string) {
      this.hostOrigin = origin
    },
    setAutoDs(autoDs?: boolean) {
      this.autoDs = !!autoDs
    },
    async setChat() {
      if (!this.assistant) {
        return null
      }
      const res = await chatApi.startAssistantChat()
      const chat: ChatInfo | undefined = chatApi.toChatInfo(res)
      return chat
    },
    clear() {
      wsCache.delete(flagKey)
      this.$reset()
    },
  },
})

export const useAssistantStore = () => {
  return AssistantStore(store)
}
