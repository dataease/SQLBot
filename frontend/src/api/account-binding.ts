import { request } from '@/utils/request'
export interface BindingCapabilities {
  show_bindings: boolean
  can_bind: boolean
}
export interface Binding {
  origin: number
  enabled: boolean
  bound: boolean
  stale: boolean
  account: string
  display_name: string
}
export interface BindingAttempt {
  origin: number
  state: string
  url: string
  callback_url: string
  expires_at: number
  client: { client_id: string; corpid: string; agent_id: string }
}
export interface BindingStatus {
  status: 'pending' | 'exchanging' | 'verified' | 'conflict' | 'failed' | 'cancelled' | 'confirmed'
  account: string
  display_name: string
}
const base = '/system/account-bindings'
const options = { requestOptions: { customError: true, retryCount: -1 } }
export const bindingApi = {
  capabilities: () => request.get<BindingCapabilities>(`${base}/capabilities`, options),
  list: () => request.get<Binding[]>(base, options),
  start: (origin: number, pwd: string, callback_url: string) =>
    request.post<BindingAttempt>(`${base}/requests`, { origin, pwd, callback_url }, options),
  status: (state: string) => request.get<BindingStatus>(`${base}/requests/${state}`, options),
  callback: (params: { state: string; code: string; ticket: string; error: string }) =>
    request.post<BindingStatus>(`${base}/callback`, params, options),
  confirm: (state: string) => request.post(`${base}/requests/${state}/confirm`, {}, options),
  cancel: (state: string) => request.delete(`${base}/requests/${state}`, options),
  refresh: (state: string) =>
    request.post<BindingAttempt>(`${base}/requests/${state}/refresh`, {}, options),
  unbind: (origin: number, pwd: string) =>
    request.post(`${base}/${origin}/unbind`, { pwd }, options),
}
