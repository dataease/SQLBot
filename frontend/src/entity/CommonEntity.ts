export interface SelectOption {
  label: string
  value: string | number
  i18nKey?: string
}

export const modelTypeOptions: SelectOption[] = [
  { label: '大语言模型', value: 0, i18nKey: 'modelType.llm' },
  /* { label: 'Anthropic', value: 1 },
  { label: 'Baidu', value: 2 },
  { label: 'iFLYTEK', value: 3 },
  { label: 'Zhipu AI', value: 4 },
  { label: 'MiniMax', value: 5 },
  { label: 'Tencent', value: 6 },
  { label: 'Other', value: 7 }, */
]

export const getModelTypeName = (value: any) => {
  const tv = parseInt(value)
  const item = modelTypeOptions.find((item) => item.value === tv)
  return item?.i18nKey || item?.label || ''
}
