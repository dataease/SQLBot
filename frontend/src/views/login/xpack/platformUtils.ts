import { request } from '@/utils/request'
export const queryClientInfo = (origin: number) => {
  const url = `/system/platform/client/${origin}`
  return request.get(url)
}
