import { request } from '@/utils/request'

export const workspaceUserList = (params: any, pageNum: number, pageSize: number) =>
  request.get(`/system/workspace/uws/pager/${pageNum}/${pageSize}`, { params })

export const workspaceOptionUserList = (params: any, pageNum: number, pageSize: number) =>
  request.get(`/system/workspace/uws/option/pager/${pageNum}/${pageSize}`, { params })

export const workspaceUwsCreate = (data: any) => request.post('/system/workspace/uws', data)
export const workspaceUwsUpdate = (data: any) => request.put('/system/workspace/uws', data)
export const workspaceCreate = (data: any) => request.post('/system/workspace', data)
export const workspaceUpdate = (data: any) => request.put('/system/workspace', data)
export const workspaceUwsDelete = (data: any) => request.delete('/system/workspace/uws', { data })
export const workspaceDelete = (id: any) => request.delete(`/system/workspace/${id}`)
export const workspaceList = () => request.get('/system/workspace')
export const workspaceDetail = (id: any) => request.get(`/system/workspace/${id}`)
export const uwsOption = (params: any) => request.get('system/workspace/uws/option', { params })

export const workspaceModelMapping = (aiModelId: any) =>
  request.get(`/system/aimodel/${aiModelId}/ws_mapping`)
export const workspaceModelMappingUpdate = (aiModelId: any, data: any) =>
  request.put(`/system/aimodel/${aiModelId}/ws_mapping`, data)
