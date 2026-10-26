<script lang="ts" setup>
import { computed, onMounted, provide, reactive, unref } from 'vue'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'
import { useI18n } from 'vue-i18n'
import PlatformParam from './xpack/PlatformParam.vue'
import { request } from '@/utils/request'
import { formatArg } from '@/utils/utils'
const { t } = useI18n()
const knowledgeFields = [
  { key: 'embedding.terminology_similarity', label: 'terminology_similarity', integer: false },
  { key: 'embedding.terminology_top_count', label: 'terminology_top_count', integer: true },
  { key: 'embedding.data_training_similarity', label: 'data_training_similarity', integer: false },
  { key: 'embedding.data_training_top_count', label: 'data_training_top_count', integer: true },
] as const

const knowledgeRows = [
  { label: 'terminology', similarity: knowledgeFields[0], count: knowledgeFields[1] },
  { label: 'sql_example', similarity: knowledgeFields[2], count: knowledgeFields[3] },
] as const

const tableFields = [
  { key: 'embedding.table_count', label: 'table_count', integer: true },
  { key: 'embedding.datasource_count', label: 'datasource_count', integer: true },
] as const
const weightField = { key: 'embedding.table_alpha', label: 'table_alpha', integer: false } as const
const numericFields = [...knowledgeFields, ...tableFields, weightField]
const booleanFields = [
  'embedding.enabled',
  'embedding.keyword_enabled',
  'embedding.table_enabled',
] as const
type NumericParameterKey = (typeof numericFields)[number]['key']
type BooleanParameterKey = (typeof booleanFields)[number]
type EmbeddingParameterForm = Partial<
  Record<NumericParameterKey, number> & Record<BooleanParameterKey, boolean>
>
interface ParameterValue {
  pkey: string
  pval: string | number | boolean | null
}
const embeddingForm = reactive<EmbeddingParameterForm>({})
const tableMatchingMode = computed(() => {
  if (!embeddingForm['embedding.table_enabled']) return 'unfiltered'
  return embeddingForm['embedding.keyword_enabled'] ? 'hybrid' : 'vector'
})
const keywordWeight = computed(() => {
  const alpha = embeddingForm['embedding.table_alpha']
  return typeof alpha === 'number' && Number.isFinite(alpha) && alpha >= 0 && alpha <= 1
    ? Number((1 - alpha).toFixed(10))
    : '—'
})
const isBooleanParameter = (key: string): key is BooleanParameterKey =>
  booleanFields.some((field) => field === key)
const isNumericParameter = (key: string): key is NumericParameterKey =>
  numericFields.some((field) => field.key === key)

const state = reactive({
  parameterForm: reactive<any>({
    'chat.sqlbot_name': 'SQLBot',
    'chat.hide_thinking_block': false,
    'chat.expand_thinking_block': false,
    'chat.limit_rows': false,
    'chat.show_sql': false,
    'chat.show_log': false,
  }),
})
provide('parameterForm', state.parameterForm)
const loadData = () => {
  request.get('/system/parameter').then((res: ParameterValue[]) => {
    if (res) {
      res.forEach((item) => {
        if (isBooleanParameter(item.pkey)) {
          embeddingForm[item.pkey] = item.pval === true || item.pval === 'true'
        } else if (isNumericParameter(item.pkey)) {
          embeddingForm[item.pkey] = Number(item.pval)
        } else if (
          item.pkey?.startsWith('chat') ||
          item.pkey?.startsWith('login') ||
          item.pkey?.startsWith('platform')
        ) {
          if (item.pkey === 'chat.sqlbot_name') {
            if (typeof item.pval === 'string' && item.pval.trim().length > 0) {
              state.parameterForm[item.pkey] = item.pval
            }
          } else {
            state.parameterForm[item.pkey] = formatArg(String(item.pval))
          }
        }
      })
    }
  })
}

const onContextRecordCountChange = (count: number) => {
  if (count < 0) {
    state.parameterForm['chat.context_record_count'] = 0
  }
  state.parameterForm['chat.context_record_count'] = Math.floor(count)
}

const beforeChange = (): Promise<boolean> => {
  return new Promise((resolve) => {
    if (!state.parameterForm['chat.rows_of_data']) {
      return resolve(true)
    }
    ElMessageBox.confirm(t('parameter.excessive_data_volume'), t('parameter.prompt'), {
      confirmButtonType: 'primary',
      confirmButtonText: t('common.confirm2'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon confirm_no_icon_parameter',
      autofocus: false,
      callback: (action: any) => {
        resolve(action && action === 'confirm')
      },
    })
  })
}
const buildParam = () => {
  const changedItemArray = Object.entries({ ...state.parameterForm, ...embeddingForm }).map(
    ([pkey, pval]) => ({
      pkey,
      pval: String(pval),
    })
  )
  const formData = new FormData()
  formData.append('data', JSON.stringify(unref(changedItemArray)))
  return formData
}
const saveHandler = () => {
  const invalid = numericFields.some(({ key, integer }) => {
    const value = embeddingForm[key]
    return (
      typeof value !== 'number' ||
      !Number.isFinite(value) ||
      (integer ? !Number.isInteger(value) || value <= 0 : value < 0 || value > 1)
    )
  })
  if (invalid || booleanFields.some((key) => typeof embeddingForm[key] !== 'boolean')) {
    ElMessage.error(t('parameter.invalid_embedding_parameter'))
    return
  }
  const param = buildParam()
  request
    .post('/system/parameter', param, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    .then(() => {
      ElMessage.success(t('common.save_success'))
      loadData()
    })
}
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="parameter">
    <div class="title">
      {{ t('parameter.parameter_configuration') }}
    </div>
    <div class="card-container">
      <div class="card">
        <div class="card-title">
          {{ t('parameter.question_count_settings') }}
        </div>
        <el-row>
          <div class="card-item" style="width: 100%">
            <div class="label">
              {{ t('parameter.sqlbot_name') }}
            </div>
            <div class="value">
              <el-input v-model="state.parameterForm['chat.sqlbot_name']" />
            </div>
          </div>
        </el-row>
        <div style="display: grid; grid-template-columns: 1fr 1fr">
          <div class="card-item">
            <div class="label">
              {{ t('parameter.hide_model_thinking_process') }}
            </div>
            <div class="value">
              <el-switch v-model="state.parameterForm['chat.hide_thinking_block']" />
            </div>
          </div>
          <div v-if="!state.parameterForm['chat.hide_thinking_block']" class="card-item">
            <div class="label">
              {{ t('parameter.model_thinking_process') }}

              <el-tooltip effect="dark" :content="t('parameter.closed_by_default')" placement="top">
                <el-icon size="16">
                  <icon_info_outlined_1></icon_info_outlined_1>
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value">
              <el-switch v-model="state.parameterForm['chat.expand_thinking_block']" />
            </div>
          </div>
          <div class="card-item">
            <div class="label">
              {{ t('parameter.rows_of_data') }}
              <el-tooltip
                effect="dark"
                :content="t('parameter.excessive_data_volume')"
                placement="top"
              >
                <el-icon size="16">
                  <icon_info_outlined_1></icon_info_outlined_1>
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value">
              <el-switch
                v-model="state.parameterForm['chat.limit_rows']"
                :before-change="beforeChange"
              />
            </div>
          </div>
          <div class="card-item">
            <div class="label">
              {{ t('parameter.show_sql') }}
            </div>
            <div class="value">
              <el-switch v-model="state.parameterForm['chat.show_sql']" />
            </div>
          </div>
          <div class="card-item">
            <div class="label">
              {{ t('parameter.show_log') }}
            </div>
            <div class="value">
              <el-switch v-model="state.parameterForm['chat.show_log']" />
            </div>
          </div>
          <div class="card-item">
            <div class="label">
              {{ t('parameter.context_record_count') }}
              <el-tooltip
                effect="dark"
                :content="t('parameter.context_record_count_hint')"
                placement="top"
              >
                <el-icon size="16">
                  <icon_info_outlined_1></icon_info_outlined_1>
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value">
              <el-input-number
                v-model.number="state.parameterForm['chat.context_record_count']"
                min="0"
                step="1"
                @change="onContextRecordCountChange"
              />
            </div>
          </div>
        </div>
      </div>

      <p class="embedding-scope hint">{{ t('parameter.embedding_scope_hint') }}</p>
      <div class="card embedding-card">
        <div class="embedding-header">
          <div class="card-title">{{ t('parameter.knowledge_retrieval') }}</div>
          <div class="embedding-toggle">
            <span>{{ t('parameter.knowledge_enabled') }}</span>
            <el-tooltip :content="t('parameter.embedding_backfill_hint')" placement="top">
              <el-switch
                v-model="embeddingForm['embedding.enabled']"
                :aria-label="
                  t('parameter.knowledge_retrieval') + ' ' + t('parameter.knowledge_enabled')
                "
              />
            </el-tooltip>
          </div>
        </div>
        <p class="hint">{{ t('parameter.knowledge_enabled_hint') }}</p>
        <div class="knowledge-table-wrapper">
          <table class="knowledge-table">
            <thead>
              <tr>
                <th scope="col">{{ t('parameter.knowledge_type') }}</th>
                <th scope="col">
                  <span class="embedding-label">
                    {{ t('parameter.similarity_threshold') }}
                    <el-tooltip :content="t('parameter.similarity_hint')" placement="top">
                      <el-icon tabindex="0" :aria-label="t('parameter.similarity_hint')">
                        <icon_info_outlined_1 />
                      </el-icon>
                    </el-tooltip>
                  </span>
                </th>
                <th scope="col">{{ t('parameter.vector_candidates') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in knowledgeRows" :key="row.label">
                <th scope="row">{{ t(`parameter.${row.label}`) }}</th>
                <td>
                  <el-input-number
                    v-model="embeddingForm[row.similarity.key]"
                    :step="0.05"
                    :disabled="!embeddingForm['embedding.enabled']"
                    :aria-label="t(`parameter.${row.similarity.label}`)"
                  />
                </td>
                <td>
                  <div class="embedding-label">
                    <el-input-number
                      v-model="embeddingForm[row.count.key]"
                      :step="1"
                      :disabled="!embeddingForm['embedding.enabled']"
                      :aria-label="t(`parameter.${row.count.label}`)"
                    />
                    <el-tooltip :content="t(`parameter.${row.label}_count_hint`)" placement="top">
                      <el-icon tabindex="0" :aria-label="t(`parameter.${row.label}_count_hint`)">
                        <icon_info_outlined_1 />
                      </el-icon>
                    </el-tooltip>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card embedding-card">
        <div class="embedding-header">
          <div class="card-title">{{ t('parameter.table_selection') }}</div>
          <div class="embedding-toggle">
            <span>{{ t('parameter.table_enabled') }}</span>
            <el-tooltip :content="t('parameter.embedding_backfill_hint')" placement="top">
              <el-switch
                v-model="embeddingForm['embedding.table_enabled']"
                :aria-label="t('parameter.table_selection') + ' ' + t('parameter.table_enabled')"
              />
            </el-tooltip>
          </div>
        </div>
        <p class="hint">{{ t('parameter.table_enabled_hint') }}</p>
        <div class="embedding-grid">
          <div v-for="field in tableFields" :key="field.key" class="card-item">
            <div class="label embedding-label">
              {{ t(`parameter.${field.label}`) }}
              <el-tooltip :content="t(`parameter.${field.label}_hint`)" placement="top">
                <el-icon tabindex="0" :aria-label="t(`parameter.${field.label}_hint`)">
                  <icon_info_outlined_1 />
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value">
              <el-input-number
                v-model="embeddingForm[field.key]"
                :step="field.integer ? 1 : 0.05"
                :disabled="!embeddingForm['embedding.table_enabled']"
                :aria-label="t(`parameter.${field.label}`)"
              />
            </div>
          </div>
        </div>
      </div>
      <div class="card embedding-card">
        <div class="embedding-header">
          <div class="card-title">{{ t('parameter.keyword_and_hybrid_matching') }}</div>
          <div class="embedding-toggle">
            <span>{{ t('parameter.keyword_enabled') }}</span>
            <el-switch
              v-model="embeddingForm['embedding.keyword_enabled']"
              :aria-label="t('parameter.keyword_enabled')"
            />
          </div>
        </div>
        <p class="hint">{{ t('parameter.keyword_enabled_hint') }}</p>
        <div class="table-matching" aria-live="polite">
          <div class="matching-mode">
            <span>{{ t('parameter.table_matching_strategy') }}</span>
            <el-tag :type="tableMatchingMode === 'unfiltered' ? 'info' : 'primary'" size="small">
              {{ t(`parameter.table_matching_${tableMatchingMode}`) }}
            </el-tag>
          </div>
          <p class="hint">{{ t(`parameter.table_matching_${tableMatchingMode}_hint`) }}</p>
          <div class="card-item">
            <div class="label embedding-label">
              {{ t('parameter.table_alpha') }}
              <el-tooltip :content="t('parameter.table_alpha_hint')" placement="top">
                <el-icon tabindex="0" :aria-label="t('parameter.table_alpha_hint')">
                  <icon_info_outlined_1 />
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value matching-weight">
              <el-input-number
                v-model="embeddingForm[weightField.key]"
                :step="0.05"
                :disabled="tableMatchingMode !== 'hybrid'"
                :aria-label="t('parameter.table_alpha')"
              />
              <span v-if="tableMatchingMode === 'hybrid'" class="hint">
                {{ t('parameter.keyword_weight', { weight: keywordWeight }) }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <platform-param />
    </div>
    <div class="save">
      <el-button type="primary" @click="saveHandler">{{ t('common.save') }}</el-button>
    </div>
  </div>
</template>
<style lang="less">
.confirm_no_icon_parameter {
  .ed-message-box__header {
    margin-bottom: var(--ed-messagebox-padding-primary);
  }
  .ed-message-box__message > p {
    font-size: 14px;
    font-weight: 400;
    line-height: 22px;
  }
}
</style>
<style lang="less" scoped>
.parameter {
  :deep(.ed-radio) {
    --ed-radio-input-height: 16px;
    --ed-radio-input-width: 16px;
  }
  .title {
    font-weight: 500;
    font-size: 20px;
    line-height: 28px;
    margin-bottom: 16px;
  }
  .embedding-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px 24px;
  }
  .embedding-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .embedding-toggle,
  .embedding-label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .embedding-toggle {
    flex-shrink: 0;
    font-size: 14px;
  }
  .embedding-label .ed-icon {
    flex-shrink: 0;
    color: var(--ed-text-color-secondary);
  }
  .table-matching {
    margin-top: 16px;
    padding: 16px;
    border-radius: 8px;
    background: var(--ed-fill-color-light);
  }
  .matching-mode,
  .matching-weight {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 14px;
  }
  .matching-weight .hint {
    margin: 0;
  }
  .knowledge-table-wrapper {
    overflow-x: auto;
    margin-top: 16px;
  }
  .knowledge-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 14px;

    th,
    td {
      padding: 12px 16px;
      font-weight: 400;
    }
    thead {
      background: var(--ed-fill-color-light);
      color: var(--ed-text-color-secondary);
    }
    tbody tr + tr {
      border-top: 1px solid var(--ed-border-color-lighter);
    }
    th:first-child {
      width: 24%;
      min-width: 110px;
    }
  }
  .save {
    position: sticky;
    bottom: 0;
    z-index: 2;
    margin-top: 16px;
    padding: 16px 0;
    background: var(--ed-bg-color);
    border-top: 1px solid var(--ed-border-color-lighter);
  }
  .hint.embedding-scope {
    margin-top: 24px;
  }
  .card-container .card.embedding-card {
    .embedding-header .card-title {
      width: auto;
    }
    .card-item {
      width: 100%;
    }
  }
  .hint {
    color: var(--ed-text-color-secondary);
    margin: 8px 0 0;
    font-size: 12px;
  }
  .card-container {
    .card {
      width: 100%;
      border-radius: 12px;
      padding: 16px;
      border: 1px solid #dee0e3;
      display: flex;
      flex-direction: column;
      margin-top: 16px;

      .card-title {
        font-weight: 500;
        font-size: 16px;
        line-height: 24px;
        width: 100%;
      }
      .card-item {
        margin-top: 16px;
        width: calc(50% - 8px);
        .label {
          font-weight: 400;
          font-size: 14px;
          line-height: 22px;
          display: flex;
          align-items: center;

          .ed-icon {
            margin-left: 4px;
          }

          .require::after {
            content: '*';
            color: var(--ed-color-danger);
            margin-left: 4px;
          }
        }

        .value {
          margin-top: 8px;
          line-height: 20px;
        }
      }
    }
  }
  @media (max-width: 960px) {
    .embedding-grid {
      grid-template-columns: 1fr;
    }
    .embedding-header {
      flex-wrap: wrap;
    }
  }
}
</style>
