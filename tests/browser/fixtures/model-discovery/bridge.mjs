// Keep the actual API wrapper; replace only its HTTP boundary with intercepted local requests.
const fixture = {
  id: "1",
  name: "数据分析助手",
  supplier: 15,
  model_type: 0,
  base_model: "demo-chat",
  api_domain: "https://gateway.example.com/v1",
  api_key: "synthetic-key",
  protocol: 1,
  config_list: [],
  ws_mapping_count: 0,
};
export const request = {
  get: async (url) =>
    url === "/system/aimodel"
      ? [{ ...fixture }]
      : url === "/system/aimodel/1"
        ? { ...fixture }
        : [],
  fetchStream: async (url, data, controller) =>
    fetch("/api" + url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal: controller?.signal,
    }),
  post: async (url, data) => {
    const response = await fetch("/api" + url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("request failed");
    return response.json();
  },
};
