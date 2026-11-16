import { request } from '@/utils/request'

export interface AgentToken {
  id: string
  name: string
  // Display prefix only, e.g. "sk-sqlbot-ab12cd34"; the secret is never listed.
  token_prefix: string
  status: boolean
  oid: string
  // null: follows the owner's datasource permissions.
  datasource_ids: string[] | null
  create_time: number
  last_used_time: number | null
  last_used_ip: string | null
}

export interface AgentTokenCreated extends AgentToken {
  // Full token, returned once by create.
  token: string
}

export interface AgentTokenCreatePayload {
  name: string
  datasource_ids: string[] | null
}

export const agentTokenApi = {
  list: (): Promise<AgentToken[]> => request.get('/system/agent-token'),
  create: (data: AgentTokenCreatePayload): Promise<AgentTokenCreated> =>
    request.post('/system/agent-token', data),
  setStatus: (id: string, status: boolean): Promise<AgentToken> =>
    request.put('/system/agent-token/status', { id, status }),
  remove: (id: string) => request.delete(`/system/agent-token/${id}`),
}
