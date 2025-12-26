import { request } from '@/utils/request'

export const audit = {
  getList: (pageNum: any, pageSize: any, params: any) =>
    request.get(`/system/audit/page/${pageNum}/${pageSize}${params}`),
  getOptions: () => request.get(`/system/audit/get_options`),
  export2Excel: (params: any) =>
    request.get(`/system/audit/export`, {
      params,
      responseType: 'blob',
      requestOptions: { customError: true },
    }),
}
