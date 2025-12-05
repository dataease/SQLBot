import { request } from '@/utils/request'

export const recommendedApi = {
  get_recommended_problem: (dsId: any) =>
    request.get(`/recommended_problem/get_datasource_recommended/${dsId}`),
  save_recommended_problem: (data: any) =>
    request.post(`/recommended_problem/save_recommended_problem`, data),
  get_datasource_recommended_base: (datasource_id?: number): Promise<any> => {
    return request.get(`/recommended_problem/get_datasource_recommended_base/${datasource_id}`)
  },
}
