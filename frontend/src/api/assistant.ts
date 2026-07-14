import { request } from '@/utils/request'

export const assistantApi = {
  queryAll: (keyword?: string) =>
    request.get('/system/assistant', { params: keyword ? { keyword } : {} }),
  add: (data: any) => request.post('/system/assistant', data),
  edit: (data: any) => request.put('/system/assistant', data),
  delete: (id: number) => request.delete(`/system/assistant/${id}`),
  // query: (id: number) => request.get(`/system/assistant/${id}`),
  validate: (data: any) => request.get('/system/assistant/validator', { params: data }),
}
