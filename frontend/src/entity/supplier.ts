import icon_alybl_colorful from '@/assets/model/icon_alybl_colorful.png'
import icon_bdyzn_colorful from '@/assets/model/icon_bdyzn_colorful.png'
import icon_deepseek_colorful from '@/assets/model/icon_deepseek_colorful.png'
import icon_txy_colorful from '@/assets/model/icon_txy_colorful.png'
import icon_xfhx_colorful from '@/assets/model/icon_xfhx_colorful.png'
import icon_gemini_colorful from '@/assets/model/icon_gemini_colorful.png'
import icon_openai_colorful from '@/assets/model/icon_openai_colorful.png'
import icon_kimi_colorful from '@/assets/model/icon_kimi_colorful.png'
import icon_txhy_colorful from '@/assets/model/icon_txhy_colorful.png'
import icon_hsyq_colorful from '@/assets/model/icon_hsyq_colorful.png'
// import icon_vllm_colorful from '@/assets/model/icon_vllm_colorful.png'
import icon_common_openai from '@/assets/model/icon_common_openai.png'
// import icon_azure_openAI_colorful from '@/assets/model/icon_Azure_OpenAI_colorful.png'

type ModelArg = { key: string; val?: string | number; type: string; range?: string }
type ModelOption = { name: string; api_domain?: string; args?: ModelArg[] }
type ModelConfig = Record<
  number,
  {
    api_domain: string
    common_args?: ModelArg[]
    model_options: ModelOption[]
  }
>

export const supplierList: Array<{
  id: number
  name: string
  i18nKey: string
  icon: any
  type?: string
  is_private?: boolean
  model_config: ModelConfig
}> = [
  {
    id: 1,
    name: '阿里云百炼',
    i18nKey: 'supplier.alibaba_cloud_bailian',
    icon: icon_alybl_colorful,
    model_config: {
      0: {
        api_domain: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        common_args: [
          { key: 'temperature', val: 1.0, type: 'number', range: '[0, 2)' },
          { key: 'extra_body', val: '{"enable_thinking": false}', type: 'json' },
        ],
        model_options: [
          { name: 'qwen3-coder-plus' },
          { name: 'qwen3-coder-flash' },
          { name: 'qwen-plus' },
          /* { name: 'qwen-plus-latest' }, */
          { name: 'qwen-max' },
          { name: 'qwen-max-latest' },
          { name: 'qwen-turbo' },
          { name: 'qwen-turbo-latest' },
          { name: 'qwen-long' },
          { name: 'qwen-long-latest' },
        ],
      },
    },
  },
  {
    id: 2,
    name: '千帆大模型',
    i18nKey: 'supplier.qianfan_model',
    icon: icon_bdyzn_colorful,
    model_config: {
      0: {
        api_domain: 'https://qianfan.baidubce.com/v2/',
        model_options: [{ name: 'ernie-x1-turbo-32k' }],
      },
    },
  },
  {
    id: 3,
    name: 'DeepSeek',
    i18nKey: 'supplier.deepseek',
    icon: icon_deepseek_colorful,
    model_config: {
      0: {
        api_domain: 'https://api.deepseek.com',
        model_options: [
          { name: 'deepseek-chat' },
          /* { name: 'deepseek-reasoner' } */
        ],
      },
    },
  },
  {
    id: 4,
    name: '腾讯混元',
    i18nKey: 'supplier.tencent_hunyuan',
    icon: icon_txhy_colorful,
    model_config: {
      0: {
        api_domain: 'https://api.hunyuan.cloud.tencent.com/v1/',
        common_args: [{ key: 'temperature', val: 1.0, type: 'number', range: '[0, 2]' }],
        model_options: [
          { name: 'hunyuan-turbos-latest' },
          /* { name: 'hunyuan-turbos-longtext-128k-20250325' },
          { name: 'hunyuan-large' }, */
          { name: 'hunyuan-standard-256K' },
          { name: 'hunyuan-standard' },
          /* { name: 'hunyuan-lite' }, */
        ],
      },
    },
  },
  {
    id: 5,
    name: '讯飞星火',
    i18nKey: 'supplier.iflytek_spark',
    icon: icon_xfhx_colorful,
    model_config: {
      0: {
        api_domain: 'https://spark-api-open.xf-yun.com/v1/',
        common_args: [
          { key: 'temperature', val: 1.0, type: 'number', range: '[0, 2]' },
          { key: 'max_tokens', val: 4096, type: 'number', range: '[1, 32768]' },
        ],
        model_options: [
          {
            name: '4.0Ultra',
            args: [
              { key: 'temperature', val: 0.5, type: 'number', range: '[0, 1]' },
              { key: 'max_tokens', val: 8192, type: 'number', range: '[1, 8192]' },
            ],
            api_domain: 'https://spark-api-open.xf-yun.com/v1/',
          },
          /* {
            name: 'generalv3.5',
            args: [{ key: 'max_tokens', val: 4096, type: 'number', range: '[1, 8192]' }],
          },
          {
            name: 'max-32k',
            args: [{ key: 'max_tokens', val: 4096, type: 'number', range: '[1, 32768]' }],
          },
          {
            name: 'generalv3',
            args: [{ key: 'max_tokens', val: 4096, type: 'number', range: '[1, 8192]' }],
          },
          {
            name: 'pro-128k',
            args: [{ key: 'max_tokens', val: 4096, type: 'number', range: '[1, 131072]' }],
          },
          {
            name: 'lite',
            args: [{ key: 'max_tokens', val: 4096, type: 'number', range: '[1, 4096]' }],
          }, */
          {
            name: 'x1',
            args: [
              { key: 'max_tokens', val: 32768, type: 'number', range: '[1, 32768]' },
              { key: 'temperature', val: 1.2, type: 'number', range: '(0, 2]' },
            ],
            api_domain: 'https://spark-api-open.xf-yun.com/v2/',
          },
        ],
      },
    },
  },
  {
    id: 6,
    name: 'Gemini',
    i18nKey: 'supplier.gemini',
    icon: icon_gemini_colorful,
    model_config: {
      0: {
        api_domain: 'https://generativelanguage.googleapis.com/v1beta/openai/',
        common_args: [{ key: 'temperature', val: 0.7, type: 'number', range: '(0, 1]' }],
        model_options: [
          { name: 'gemini-2.5-pro' },
          { name: 'gemini-2.5-flash' },
          { name: 'gemini-2.5-flash-lite' },
          { name: 'gemini-2.0-flash' },
          { name: 'gemini-2.0-flash-lite' },
        ],
      },
    },
  },
  {
    id: 7,
    name: 'OpenAI',
    i18nKey: 'supplier.openai',
    icon: icon_openai_colorful,
    model_config: {
      0: {
        api_domain: 'https://api.openai.com/v1',
        common_args: [{ key: 'temperature', val: 1.0, type: 'number', range: '[0, 2]' }],
        model_options: [
          { name: 'gpt-4.1' },
          { name: 'gpt-4.1-mini' },
          { name: 'gpt-4.1-nano' },
          { name: 'gpt-4o' },
          { name: 'gpt-4o-mini' },
          { name: 'chatgpt-4o' },
          { name: 'o4-mini' },
          { name: 'o4-mini-deep-research' },
          { name: 'o3' },
          { name: 'o3-pro' },
          { name: 'o3-mini' },
          { name: 'o3-deep-research' },
          { name: 'o1' },
          { name: 'o1-pro' },
          { name: 'o1-mini' },
        ],
      },
    },
  },
  {
    id: 8,
    name: 'Kimi',
    i18nKey: 'supplier.kimi',
    icon: icon_kimi_colorful,
    model_config: {
      0: {
        api_domain: 'https://api.moonshot.cn/v1',
        common_args: [{ key: 'temperature', val: 0.3, type: 'number', range: '[0, 1]' }],
        model_options: [
          {
            name: 'kimi-k2-0711-preview',
            args: [{ key: 'temperature', val: 0.3, type: 'number', range: '[0, 1]' }],
          },
          {
            name: 'kimi-k2-turbo-preview',
            args: [{ key: 'temperature', val: 0.3, type: 'number', range: '[0, 1]' }],
          },
          { name: 'moonshot-v1-8k' },
          { name: 'moonshot-v1-32k' },
          { name: 'moonshot-v1-128k' },
          { name: 'moonshot-v1-auto' },
          { name: 'kimi-latest' },
          { name: 'moonshot-v1-8k-vision-preview' },
          { name: 'moonshot-v1-32k-vision-preview' },
          { name: 'moonshot-v1-128k-vision-preview' },
          { name: 'kimi-thinking-preview' },
        ],
      },
    },
  },
  {
    id: 9,
    name: '腾讯云',
    i18nKey: 'supplier.tencent_cloud',
    icon: icon_txy_colorful,
    model_config: {
      0: {
        api_domain: 'https://api.lkeap.cloud.tencent.com/v1',
        common_args: [{ key: 'temperature', val: 0.6, type: 'number', range: '[0, 1]' }],
        model_options: [
          { name: 'deepseek-r1' },
          { name: 'deepseek-r1-0528' },
          { name: 'deepseek-v3' },
          { name: 'deepseek-v3-0324' },
        ],
      },
    },
  },
  {
    id: 10,
    name: '火山引擎',
    i18nKey: 'supplier.volcano_engine',
    icon: icon_hsyq_colorful,
    model_config: {
      0: {
        api_domain: 'https://ark.cn-beijing.volces.com/api/v3',
        common_args: [{ key: 'temperature', val: 0.6, type: 'number', range: '[0, 1]' }],
        model_options: [
          { name: 'doubao-seed-1-6-250615' },
          { name: 'doubao-seed-1-6-flash-250715' },
          { name: 'doubao-1-5-pro-32k-character-250715' },
          { name: 'kimi-k2-250711' },
          { name: 'deepseek-v3-250324' },
          { name: 'deepseek-r1' },
        ],
      },
    },
  },
  /* {
    id: 11,
    name: 'vLLM',
    icon: icon_vllm_colorful,
    type: 'vllm',
    is_private: true,
    model_config: {
      0: {
        api_domain: 'http://127.0.0.1:8000/v1',
        common_args: [{ key: 'temperature', val: 0.6, type: 'number', range: '[0, 1]' }],
        model_options: [],
      },
    },
  }, */
  /* {
    id: 12,
    name: 'Azure OpenAI',
    icon: icon_azure_openAI_colorful,
    type: 'azure',
    is_private: true,
    model_config: {
      0: {
        api_domain: 'https://{your resource name}.openai.azure.cn/',
        common_args: [{ key: 'temperature', val: 0.6, type: 'number', range: '[0, 1]' }],
        model_options: [
          {
            name: 'Azure OpenAI',
            args: [
              { key: 'api_version', val: '2024-02-15-preview', type: 'string' },
              { key: 'deployment_name', val: '', type: 'string' },
            ],
          },
          {
            name: 'gpt-4',
            args: [
              { key: 'api_version', val: '2024-02-15-preview', type: 'string' },
              { key: 'deployment_name', val: '', type: 'string' },
            ],
          },
        ],
      },
    },
  }, */
  {
    id: 15,
    name: '通用OpenAI',
    i18nKey: 'supplier.generic_openai',
    icon: icon_common_openai,
    is_private: true,
    model_config: {
      0: {
        api_domain: 'http://127.0.0.1:8000/v1',
        common_args: [{ key: 'temperature', val: 0.6, type: 'number', range: '[0, 1]' }],
        model_options: [
          { name: 'gpt-4.1' },
          { name: 'gpt-4.1-mini' },
          { name: 'gpt-4.1-nano' },
          { name: 'gpt-4o' },
          { name: 'gpt-4o-mini' },
          { name: 'chatgpt-4o' },
          { name: 'o4-mini' },
          { name: 'o4-mini-deep-research' },
          { name: 'o3' },
          { name: 'o3-pro' },
          { name: 'o3-mini' },
          { name: 'o3-deep-research' },
          { name: 'o1' },
          { name: 'o1-pro' },
          { name: 'o1-mini' },
        ],
      },
    },
  },
]

export const base_model_options = (supplier_id: number, model_type?: number) => {
  const supplier = get_supplier(supplier_id)
  return supplier?.model_config[model_type || 0].model_options
}

export const get_supplier = (supplier_id: number) => {
  return supplierList.find((item: any) => item.id === supplier_id)
}
