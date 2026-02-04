import { defineStore } from 'pinia'
import { store } from './index'
import { chatApi, ChatInfo } from '@/api/chat'
import { useCache } from '@/utils/useCache'

const { wsCache } = useCache()
const flagKey = 'sqlbit-assistant-flag'
type Resolver<T = any> = (value: T | PromiseLike<T>) => void
type Rejecter = (reason?: any) => void
interface PendingRequest<T = any> {
  requestId: string
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
  requestPromiseMap: Map<string, PendingRequest[]>
  pedding: boolean
  certificateTime: number
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
      requestPromiseMap: new Map<string, PendingRequest[]>(),
      pedding: false,
      certificateTime: 0,
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
    refreshCertificate<T>(requestUrl?: string) {
      if (+new Date() > this.certificateTime + 5000) {
        return
      }
      const timeout = 5000
      let peddingList = this.requestPromiseMap.get(this.id)
      if (!peddingList) {
        this.requestPromiseMap.set(this.id, [])
        peddingList = this.requestPromiseMap.get(this.id)
      }

      const removeRequest = (requestId: string) => {
        if (!peddingList) return
        let len = peddingList.length
        while (len--) {
          const peddingRequest = peddingList[len]
          if (peddingRequest?.requestId === requestId) {
            peddingList.splice(len, 1)
          }
        }
      }

      const addRequest = (requestId: string, resolve: any, reject: any) => {
        const currentPeddingRequest = {
          requestId,
          resolve: (value: T) => {
            removeRequest(requestId)
            resolve(value)
          },
          reject: (reason: any) => {
            removeRequest(requestId)
            reject(reason)
          },
        } as PendingRequest
        peddingList?.push(currentPeddingRequest)
      }

      return new Promise((resolve, reject) => {
        const currentRequestId = `${this.id}|${+new Date()}`
        const timeoutId = setTimeout(() => {
          removeRequest(currentRequestId)
          console.error(`Request ${currentRequestId}[${requestUrl}] timed out after ${timeout}ms`)
          resolve(null)
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          // reject(new Error(`Request ${this.id} timed out after ${timeout}ms`))
        }, timeout)

        const cleanupAndResolve = (value: any) => {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          resolve(value)
        }

        const cleanupAndReject = (reason: any) => {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          reject(reason)
        }

        addRequest(currentRequestId, cleanupAndResolve, cleanupAndReject)
        if (!this.pedding) {
          const readyData = {
            eventName: this.pageEmbedded ? 'sqlbot_embedded_event' : 'sqlbot_assistant_event',
            busi: 'ready',
            ready: true,
            messageId: this.id,
          }
          window.parent.postMessage(readyData, '*')
          this.pedding = true
        }
      })
    },
    resolveCertificate(data?: any) {
      const peddingRequestList = this.requestPromiseMap.get(this.id)
      if (peddingRequestList?.length) {
        peddingRequestList.forEach((peddingRequest: PendingRequest) => {
          peddingRequest.resolve(data)
        })
      }
      this.pedding = false
      /* const resolvePromiseList = [] as Promise<void>[]
      if (peddingRequestList?.length) {
        peddingRequestList.forEach((peddingRequest: PendingRequest) => {
          const resolvePromise = new Promise((r: any) => {
            peddingRequest.resolve(data)
            r()
          })
          resolvePromiseList.push(resolvePromise as Promise<void>)
        })
      }
      if (resolvePromiseList?.length) {
        Promise.all(resolvePromiseList).then(() => {
          this.pedding = false
        })
      } else {
        this.pedding = false
      } */
    },
    setId(id: string) {
      this.id = id
    },
    setCertificate(certificate: string) {
      this.certificate = certificate
      this.certificateTime = +new Date()
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
