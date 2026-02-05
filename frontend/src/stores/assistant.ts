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
  peddingStatus: number //0: ready,1: pedding,2:finish
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
      peddingStatus: 0,
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
    refreshCertificate(requestUrl?: string) {
      /* if (+new Date() < this.certificateTime + 5000) {
        return
      } */

      const timeout = 30000
      let peddingList = this.requestPromiseMap.get(this.id) as PendingRequest[]
      if (!peddingList) {
        this.requestPromiseMap.set(this.id, [])
        peddingList = this.requestPromiseMap.get(this.id) as PendingRequest[]
      }

      if (this.peddingStatus === 2) {
        if (peddingList?.length) {
          return
        } else {
          this.peddingStatus = 0
        }
      }

      return new Promise((resolve, reject) => {
        const currentRequestId = `${this.id}|${requestUrl}|${+new Date()}`
        const timeoutId = setTimeout(() => {
          console.error(`Request ${currentRequestId}[${requestUrl}] timed out after ${timeout}ms`)
          resolve(null)
          removeRequest(currentRequestId, peddingList)
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
          removeRequest(currentRequestId, peddingList)
        }

        const cleanupAndReject = (reason: any) => {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          removeRequest(currentRequestId, peddingList)
          reject(reason)
        }

        addRequest(currentRequestId, cleanupAndResolve, cleanupAndReject, peddingList)
        if (this.peddingStatus !== 1) {
          this.peddingStatus = 1
          const readyData = {
            eventName: this.pageEmbedded ? 'sqlbot_embedded_event' : 'sqlbot_assistant_event',
            busi: 'ready',
            ready: true,
            messageId: this.id,
          }
          window.parent.postMessage(readyData, '*')
        }
      })
    },
    resolveCertificate(data?: any) {
      const peddingRequestList = this.requestPromiseMap.get(this.id)

      if (peddingRequestList?.length) {
        let len = peddingRequestList?.length
        while (len--) {
          const peddingRequest: PendingRequest = peddingRequestList[len]
          peddingRequest.resolve(data)
        }
      }
      this.peddingStatus = 2
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

const removeRequest = (requestId: string, peddingList: PendingRequest[]) => {
  if (!peddingList) return
  let len = peddingList.length
  while (len--) {
    const peddingRequest = peddingList[len]
    if (peddingRequest?.requestId === requestId) {
      peddingList.splice(len, 1)
    }
  }
}

const addRequest = (
  requestId: string,
  resolve: any,
  reject: any,
  peddingList: PendingRequest[]
) => {
  const currentPeddingRequest = {
    requestId,
    resolve: (value: any) => {
      resolve(value)
    },
    reject: (reason: any) => {
      reject(reason)
    },
  } as PendingRequest
  peddingList?.push(currentPeddingRequest)
}

export const useAssistantStore = () => {
  return AssistantStore(store)
}
