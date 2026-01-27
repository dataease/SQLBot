import { request } from '@/utils/request'

export const variablesApi = {
  save: (data: any) => request.post('/sys_variable/save', data),
  listAll: () => request.post('/sys_variable/listAll', {}),
  listPage: (pageNum: any, pageSize: any, data: any) =>
    request.post(`/sys_variable/listPage/${pageNum}/${pageSize}`, data),
  delete: (data: any) => request.post(`/sys_variable/delete`, data),
}
