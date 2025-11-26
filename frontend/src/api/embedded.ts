import { request } from '@/utils/request'

export const getList = () => request.get('/system/assistant')
export const getAdvancedApplicationList = () =>
  request.get('/system/assistant/advanced_application')
export const updateAssistant = (data: any) => request.put('/system/assistant', data)
export const saveAssistant = (data: any) => request.post('/system/assistant', data)
export const getOne = (id: any) => request.get(`/system/assistant/${id}`)
export const delOne = (id: any) => request.delete(`/system/assistant/${id}`)
export const dsApi = (id: any) => request.get(`/datasource/ws/${id}`)

export const embeddedApi = {
  getList: (pageNum: any, pageSize: any, params: any) =>
    request.get(`/system/embedded/${pageNum}/${pageSize}`, {
      params,
    }),
  secret: (id: any) => request.patch(`/system/embedded/secret/${id}`),
  updateEmbedded: (data: any) => request.put('/system/embedded', data),
  addEmbedded: (data: any) => request.post('/system/embedded', data),
  deleteEmbedded: (params: any) => request.delete('/system/embedded', { data: params }),
  getOne: (id: any) => request.get(`/system/embedded/${id}`),
}
