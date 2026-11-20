import { reactive } from 'vue';
const user = reactive({ getName: '林晓', getAccount: 'lin.xiao', getEmail: 'lin.xiao@example.com', getOid: '1', getOrigin: Number(new URLSearchParams(location.search).get('origin') || 0), isAdmin: new URLSearchParams(location.search).get('role') === 'admin' });
export const useUserStore = () => user;
window.bindingFixture = { user };

export const getSQLBotAddr = () => location.origin + '/';
const call = async (method, url, body) => {
  const response = await fetch('/api' + url, { method, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw { isAxiosError: true, response: { data } };
  return data;
};
export const request = { get: url => call('GET', url), post: (url, body) => call('POST', url, body), delete: url => call('DELETE', url) };
