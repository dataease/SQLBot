import { request } from '@/utils/request'

export const settingsApi = {
  pager: (pageNumber: number, pageSize: number) =>
    request.get(`/settings/terminology/pager/${pageNumber}/${pageSize}`),
  add: (data: any) => request.post('/settings/terminology', data),
  edit: (data: any) => request.put('/settings/terminology', data),
  delete: (id: number) => request.delete(`/settings/terminology/${id}`),
  query: (id: number) => request.get(`/settings/terminology/${id}`),

  downloadError: (path: any) =>
    request.post(
      `/system/download-fail-info`,
      { file: path },
      {
        responseType: 'blob',
        requestOptions: { customError: true },
      }
    ),

  downloadTemplate: (url: any) =>
    request.get(url, {
      responseType: 'blob',
      requestOptions: { customError: true },
    }),
}
