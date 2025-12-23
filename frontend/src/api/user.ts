import { request } from '@/utils/request'

export const userImportApi = {
  downExcelTemplateApi: () => request.get('/user/template', { responseType: 'blob' }),
  importUserApi: (data: any) =>
    request.post('/user/batchImport', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downErrorRecordApi: (key: string) =>
    request.get(`/user/errorRecord/${key}`, { responseType: 'blob' }),
  clearErrorApi: (key: string) => {
    request.get(`/user/clearErrorRecord/${key}`)
  },
}

export const userApi = {
  pager: (params: any, pageNumber: number, pageSize: number) =>
    request.get(`/user/pager/${pageNumber}/${pageSize}${params}`),
  add: (data: any) => request.post('/user', data),
  edit: (data: any) => request.put('/user', data),
  clearErrorApi: (key: string) => request.get(`/user/clearErrorRecord/${key}`),
  delete: (key: string) => request.delete(`/user/${key}`),
  deleteBatch: (data: any) => request.delete(`/user`, { data }),
  get: (key: string) => request.get(`/user/${key}`),
  pwd: (id: any) => request.patch(`/user/pwd/${id}`),
  status: (data: any) => request.patch('/user/status', data),
  defaultPwd: () => request.get('/user/defaultPwd'),
}
