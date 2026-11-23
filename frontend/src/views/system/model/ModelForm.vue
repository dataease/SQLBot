<script lang="ts" setup>
import { ref, reactive, onMounted, nextTick, computed, watch, onBeforeUnmount } from 'vue'
import icon_refresh from '@/assets/embedded/icon_refresh_outlined.svg'
import arrow_down from '@/assets/svg/arrow-down.svg'
import dashboard_info from '@/assets/svg/dashboard-info.svg'
import icon_edit_outlined from '@/assets/svg/icon_edit_outlined.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import { modelApi } from '@/api/system'
import ParamsForm from './ParamsForm.vue'
import { modelTypeOptions } from '@/entity/CommonEntity.ts'
import { base_model_options, get_supplier } from '@/entity/supplier'
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    activeName: string
    editModel: boolean
  }>(),
  {
    activeName: '',
    editModel: false,
  }
)

interface ParamsFormData {
  key?: string
  val?: string
  name?: string
  id?: string
}
const { t } = useI18n()

const modelForm = reactive({
  id: '',
  supplier: 0,
  name: '',
  model_type: 0,
  base_model: '',
  api_key: '',
  api_domain: '',
  config_list: [],
  protocol: 1,
})
const isCreate = ref(false)
const modelRef = ref()
const paramsFormRef = ref()
const advancedSetting = ref([] as ParamsFormData[])
const paramsFormDrawer = ref(false)
const configExpand = ref(true)
let tempConfigMap = new Map<string, Array<any>>()

const modelSelected = computed(() => {
  return !!modelForm.base_model
})
const currentSupplier = computed(() => {
  if (!modelForm.supplier) {
    return null
  }
  return get_supplier(modelForm.supplier)
})
const modelList = computed(() => {
  if (!modelForm.supplier) {
    return []
  }
  return base_model_options(modelForm.supplier, modelForm.model_type)
})
// OpenAI-compatible chat does not guarantee a models endpoint; failures remain non-blocking.
const canDiscoverModels = computed(
  () =>
    !!currentSupplier.value &&
    modelForm.protocol === 1 &&
    !['azure', 'vllm'].includes(currentSupplier.value.type || '')
)
const discoveredModels = ref<string[]>([])
const discovering = ref(false)
const discoveryMessage = ref('')
const discoveryErrorDetail = ref('')
const discoveryState = ref<'idle' | 'success' | 'empty' | 'error'>('idle')
let discoveryVersion = 0
let initializing = false
let selectedModelDomain = ''
const invalidateDiscovery = () => {
  discoveryVersion++
  discovering.value = false
  discoveredModels.value = []
  discoveryMessage.value = ''
  discoveryState.value = 'idle'
  discoveryErrorDetail.value = ''
}
watch(() => [modelForm.api_domain, modelForm.api_key, modelForm.supplier], invalidateDiscovery, {
  flush: 'sync',
})
watch(
  () => modelForm.api_domain,
  () => {
    if (canDiscoverModels.value && !initializing && modelForm.api_key) {
      modelForm.api_key = ''
      ElMessage.info(t('model.discovery_key_reset'))
    }
  },
  { flush: 'sync' }
)
onBeforeUnmount(invalidateDiscovery)
const fetchModels = async () => {
  if (!canDiscoverModels.value || discovering.value || !modelForm.api_domain.trim()) return
  const version = ++discoveryVersion
  discovering.value = true
  discoveryMessage.value = ''
  discoveryErrorDetail.value = ''
  try {
    const result = await modelApi.discover(modelForm.api_domain, modelForm.api_key)
    if (version !== discoveryVersion) return
    if (result.error || result.error_code) {
      discoveryState.value = 'error'
      const messages = new Map([
        ['timeout', 'model.discovery_timeout'],
        ['address', 'model.discovery_address'],
        ['credentials', 'model.discovery_credentials'],
        ['unsupported', 'model.discovery_unsupported'],
        ['invalid', 'model.discovery_invalid'],
      ])
      discoveryMessage.value = t(messages.get(result.error_code || '') || 'model.discovery_failed')
      discoveryErrorDetail.value = discoveryMessage.value
      return
    }
    const ids = result.models
    discoveryState.value = ids.length ? 'success' : 'empty'
    discoveredModels.value = [...new Set(ids)]
    discoveryMessage.value = ids.length
      ? t('model.discovery_success', { count: discoveredModels.value.length })
      : t('model.discovery_empty')
  } catch {
    if (version === discoveryVersion) {
      discoveryState.value = 'error'
      discoveryMessage.value = t('model.discovery_failed')
    }
  } finally {
    if (version === discoveryVersion) discovering.value = false
  }
}
const selectableModels = computed(() => {
  // Successful discovery is authoritative; built-ins remain a fallback for manual setup.
  const candidates =
    discoveryState.value === 'success'
      ? discoveredModels.value.map((name) => ({ name }))
      : modelList.value || []
  const models: { name: string; source: string }[] = []
  const names = new Set<string>()
  for (const item of candidates) {
    if (!names.has(item.name)) {
      models.push({
        name: item.name,
        source:
          discoveryState.value === 'success'
            ? 'discovery_source_service'
            : 'discovery_source_builtin',
      })
      names.add(item.name)
    }
  }
  for (const name of [modelForm.base_model]) {
    if (name && !names.has(name)) {
      models.push({
        name,
        source: ['success', 'empty'].includes(discoveryState.value)
          ? 'discovery_source_missing'
          : 'discovery_source_current',
      })
      names.add(name)
    }
  }
  return models
})
const handleParamsEdite = (ele?: any) => {
  isCreate.value = false
  paramsFormDrawer.value = true
  nextTick(() => {
    paramsFormRef.value.initForm(ele)
  })
}

const handleParamsCreate = () => {
  isCreate.value = true
  paramsFormDrawer.value = true
  nextTick(() => {
    paramsFormRef.value.initForm()
  })
}

const handleParamsDel = (item: any) => {
  advancedSetting.value = advancedSetting.value.filter((ele) => ele.id !== item.id)
  tempConfigMap.set(`${modelForm.supplier}-${modelForm.base_model}`, [...advancedSetting.value])
}
const currentPage = ref(1)
const advancedSettingPagination = computed(() => {
  return advancedSetting.value.slice(currentPage.value * 5 - 5, currentPage.value * 5)
})

const handleCurrentChange = (val: any) => {
  currentPage.value = val
}

const rules = computed(() => ({
  model_type: [
    {
      required: true,
      message: 'type',
      trigger: 'change',
    },
  ],
  api_domain: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.api_domain_name'),
      trigger: 'blur',
    },
  ],
  base_model: [{ required: true, message: t('model.the_basic_model_de'), trigger: 'change' }],
  name: [
    { required: true, message: t('model.the_basic_model'), trigger: 'blur' },
    {
      max: 100,
      message: t('model.length_max_error', { msg: t('model.model_name'), max: 100 }),
      trigger: 'blur',
    },
  ],
  api_key: [
    {
      required: !currentSupplier.value?.is_private,
      message: t('datasource.please_enter') + t('common.empty') + 'API Key',
      trigger: 'blur',
    },
  ],
}))

onMounted(() => {
  setTimeout(() => {
    modelRef.value.clearValidate()
  }, 100)
})

const addParams = () => {
  paramsFormRef.value.submit()
}

const duplicateName = async (item: any) => {
  const arr = advancedSetting.value.filter((ele: any) => ele.id !== item.id)
  const names = arr.map((ele: any) => ele.name)
  const keys = arr.map((ele: any) => ele.key)
  if (names.includes(item.name)) {
    ElMessage.error(t('embedded.duplicate_name'))
    return
  }

  if (keys.includes(item.key)) {
    ElMessage.error(t('embedded.repeating_parameters'))
    return
  }

  if (isCreate.value) {
    advancedSetting.value.push({ ...item, id: +new Date() })
    beforeClose()
    tempConfigMap.set(`${modelForm.supplier}-${modelForm.base_model}`, [...advancedSetting.value])
    return
  }
  for (const key in advancedSetting.value) {
    const element = advancedSetting.value[key]
    if (element.id === item.id) {
      Object.assign(element, { ...item })
    }
  }
  tempConfigMap.set(`${modelForm.supplier}-${modelForm.base_model}`, [...advancedSetting.value])
  beforeClose()
}

const submit = (item: any) => {
  duplicateName(item)
}

const beforeClose = () => {
  paramsFormRef.value.close()
  paramsFormDrawer.value = false
}
const supplierChang = (supplier: any) => {
  initializing = true
  invalidateDiscovery()
  modelForm.api_key = ''
  modelForm.supplier = supplier.id
  const config = supplier.model_config[modelForm.model_type || 0]
  modelForm.api_domain = config.api_domain
  selectedModelDomain = config.api_domain
  modelForm.base_model = ''
  modelForm.protocol = supplier.type === 'vllm' ? 2 : 1
  advancedSetting.value = []
  initializing = false
}
let curId = +new Date()
const initForm = (item?: any) => {
  initializing = true
  invalidateDiscovery()
  modelForm.id = ''
  modelRef.value.clearValidate()
  tempConfigMap = new Map<string, Array<any>>()
  if (item) {
    Object.assign(modelForm, { ...item })
    selectedModelDomain =
      modelList.value?.find((model) => model.name === item.base_model)?.api_domain ||
      getSupplierDomain() ||
      ''
    if (item?.config_list?.length) {
      advancedSetting.value = item.config_list
      advancedSetting.value.forEach((ele: any) => {
        if (!ele.id) {
          ele.id = curId
          curId += 1
        }
      })
    } else {
      advancedSetting.value = []
    }
    tempConfigMap.set(`${modelForm.supplier}-${modelForm.base_model}`, [...advancedSetting.value])
  }
  initializing = false
}
const formatAdvancedSetting = (list: Array<any>) => {
  const setting_list = [
    ...list.map((item) => {
      return { id: ++curId, name: item.name, key: item.key, val: item.val } as any
    }),
  ]
  advancedSetting.value = setting_list
}
const baseModelChange = (val: string) => {
  if (!val || !modelForm.supplier) {
    return
  }
  const current_model = modelList.value?.find((model: any) => model.name == val)
  const nextDomain = current_model?.api_domain || getSupplierDomain() || ''
  // Follow built-in per-model endpoints only while the address still uses the previous default.
  // Preserve custom addresses and invalidate credentials/results if the endpoint changes.
  if (
    current_model &&
    (!canDiscoverModels.value ||
      modelForm.api_domain === (selectedModelDomain || getSupplierDomain()))
  ) {
    modelForm.api_domain = nextDomain
  }
  selectedModelDomain = nextDomain
  const current_config_list = tempConfigMap.get(`${modelForm.supplier}-${modelForm.base_model}`)
  if (current_config_list) {
    formatAdvancedSetting(current_config_list)
    return
  }
  const defaultArgs = getModelDefaultArgs()
  if (defaultArgs?.size) {
    const defaultArgsList = [...defaultArgs.values()]
    formatAdvancedSetting(defaultArgsList)
    tempConfigMap.set(`${modelForm.supplier}-${modelForm.base_model}`, [...advancedSetting.value])
  }
}
const getSupplierDomain = () => {
  return currentSupplier.value?.model_config[modelForm.model_type || 0].api_domain
}
const getModelDefaultArgs = () => {
  if (!modelForm.supplier || !modelForm.base_model) {
    return null
  }
  const model_config = currentSupplier.value?.model_config[modelForm.model_type || 0]
  const common_args = [...(model_config?.common_args || [])]
  const current_model = modelList.value?.find((model: any) => model.name == modelForm.base_model)

  if (current_model?.args?.length) {
    const modelArgs = current_model.args
    common_args.push(...modelArgs)
  }
  const argMap = common_args.reduce((acc: any, item: any) => {
    acc.set(item.key, { ...item, name: item.key })
    return acc
  }, new Map())
  return argMap
}
const emits = defineEmits(['submit'])

const submitModel = () => {
  modelRef.value.validate((res: any) => {
    if (res) {
      emits('submit', {
        ...modelForm,
        config_list: [
          ...advancedSetting.value.map((item) => {
            return { key: item.key, name: item.name, val: item.val }
          }),
        ],
      })
    }
  })
}

defineExpose({
  initForm,
  submitModel,
  supplierChang,
})
</script>

<template>
  <div class="model-form" :class="editModel && 'is-edit_model'">
    <div v-if="!editModel" class="model-name">{{ activeName }}</div>
    <el-scrollbar>
      <div class="form-content">
        <el-form
          ref="modelRef"
          :rules="rules"
          :validate-on-rule-change="false"
          label-position="top"
          :model="modelForm"
          style="width: 100%"
          @submit.prevent
        >
          <el-form-item class="custom-require flex-inline" prop="name">
            <template #label
              ><span class="custom-require_danger">{{ t('model.model_name') }}</span>
              <el-tooltip effect="dark" :content="t('model.custom_model_name')" placement="right">
                <el-icon style="margin-left: 4px" size="16">
                  <dashboard_info></dashboard_info>
                </el-icon>
              </el-tooltip>
            </template>
            <el-input
              v-model="modelForm.name"
              clearable
              :placeholder="
                $t('datasource.please_enter') + $t('common.empty') + $t('model.model_name')
              "
            />
          </el-form-item>
          <el-form-item prop="type" :label="t('model.model_type')">
            <el-select v-model="modelForm.model_type" style="width: 100%" disabled>
              <el-option
                v-for="item in modelTypeOptions"
                :key="item.value"
                :label="item.i18nKey ? $t(item.i18nKey) : item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            v-if="canDiscoverModels"
            prop="api_domain"
            :label="t('model.api_domain_name')"
          >
            <el-input
              v-model="modelForm.api_domain"
              clearable
              :placeholder="
                $t('datasource.please_enter') + $t('common.empty') + $t('model.api_domain_name')
              "
            />
          </el-form-item>
          <el-form-item v-if="canDiscoverModels" prop="api_key" label="API Key">
            <el-input
              v-model="modelForm.api_key"
              clearable
              :placeholder="$t('datasource.please_enter') + $t('common.empty') + 'API Key'"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item
            class="custom-require"
            :class="canDiscoverModels && 'discovery-base-model'"
            prop="base_model"
          >
            <template #label
              ><span class="custom-require_danger">{{ t('model.basic_model') }}</span>
              <span v-if="!canDiscoverModels" class="enter">{{ t('model.enter_to_add') }}</span>
              <el-button
                v-if="canDiscoverModels"
                class="discovery-button"
                text
                :loading="discovering"
                :disabled="discovering || !modelForm.api_domain.trim()"
                @click="fetchModels"
              >
                <el-icon v-if="!discovering"><icon_refresh /></el-icon>
                {{
                  t(
                    discovering
                      ? 'model.discovery_loading'
                      : discoveryState === 'error'
                        ? 'model.discovery_retry'
                        : 'model.discovery_fetch'
                  )
                }}
              </el-button>
            </template>
            <el-select
              v-model="modelForm['base_model']"
              style="width: 100%"
              :popper-class="canDiscoverModels ? 'discovery-model-options' : ''"
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              @change="baseModelChange"
            >
              <el-option
                v-for="item in selectableModels"
                :key="item.name"
                :label="item.name"
                :value="item.name"
                :aria-label="item.name"
                :aria-description="canDiscoverModels ? t(`model.${item.source}`) : undefined"
              >
                <div class="model-option-row">
                  <span class="model-option-name">{{ item.name }}</span>
                  <span v-if="canDiscoverModels" class="model-option-source">{{
                    t(`model.${item.source}`)
                  }}</span>
                </div>
              </el-option>
              <template v-if="canDiscoverModels" #footer
                ><span class="discovery-select-hint">{{
                  t('model.discovery_input_hint')
                }}</span></template
              >
            </el-select>
            <div v-if="canDiscoverModels" class="discovery-status-slot">
              <div
                v-if="discoveryMessage"
                class="discovery-status"
                :class="discoveryState"
                :title="discoveryState === 'error' ? discoveryErrorDetail : undefined"
                role="status"
              >
                {{ discoveryMessage }}
              </div>
            </div>
          </el-form-item>
          <el-form-item
            v-if="modelSelected && !canDiscoverModels"
            prop="api_domain"
            :label="t('model.api_domain_name')"
          >
            <el-input
              v-model="modelForm.api_domain"
              clearable
              :placeholder="
                $t('datasource.please_enter') + $t('common.empty') + $t('model.api_domain_name')
              "
            />
          </el-form-item>
          <el-form-item v-if="modelSelected && !canDiscoverModels" prop="api_key" label="API Key">
            <el-input
              v-model="modelForm.api_key"
              clearable
              :placeholder="$t('datasource.please_enter') + $t('common.empty') + 'API Key'"
              type="password"
              show-password
            />
          </el-form-item>
        </el-form>
        <div
          v-if="modelSelected"
          class="advance-setting"
          :class="configExpand && 'expand'"
          @click="configExpand = !configExpand"
        >
          {{ t('model.advanced_settings') }}
          <el-icon size="16">
            <arrow_down></arrow_down>
          </el-icon>
        </div>
        <div v-if="modelSelected && configExpand" class="model-params">
          {{ t('model.model_parameters') }}
          <span class="btn" @click="handleParamsCreate">
            <el-icon size="16">
              <icon_add_outlined></icon_add_outlined>
            </el-icon>
            {{ t('model.add') }}
          </span>
        </div>

        <div
          v-if="modelSelected && configExpand"
          class="params-table"
          :class="!advancedSettingPagination.length && 'bottom-border'"
        >
          <el-table :data="advancedSettingPagination" style="width: 100%">
            <el-table-column prop="key" :label="t('model.parameters')" width="280" />
            <el-table-column prop="name" :label="t('model.display_name')" width="280" />
            <el-table-column prop="val" show-overflow-tooltip :label="t('model.parameter_value')" />
            <el-table-column
              fixed="right"
              width="80"
              class-name="operation-column_text"
              :label="$t('ds.actions')"
            >
              <template #default="scope">
                <el-button text type="primary" @click="handleParamsEdite(scope.row)">
                  <el-icon size="16">
                    <icon_edit_outlined></icon_edit_outlined>
                  </el-icon>
                </el-button>
                <el-button text type="primary" @click="handleParamsDel(scope.row)">
                  <el-icon size="16">
                    <icon_delete></icon_delete>
                  </el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div
          v-if="modelSelected && advancedSetting.length > 5 && configExpand"
          class="params-table_pagination"
        >
          <el-pagination
            :default-page-size="5"
            layout="prev, pager, next"
            :total="advancedSetting.length"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-scrollbar>
    <el-drawer
      v-model="paramsFormDrawer"
      :size="600"
      :before-close="beforeClose"
      :title="
        isCreate
          ? $t('model.add') + $t('common.empty') + $t('model.parameters')
          : $t('datasource.edit') + $t('common.empty') + $t('model.parameters')
      "
    >
      <ParamsForm ref="paramsFormRef" @submit="submit"></ParamsForm>
      <template #footer>
        <el-button secondary @click="beforeClose"> {{ $t('common.cancel') }} </el-button>
        <el-button type="primary" @click="addParams">
          {{ isCreate ? t('model.add') : t('common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="less" scoped>
.model-form {
  width: calc(100% - 280px);
  position: absolute;
  right: 0;
  top: 56px;
  height: calc(100% - 120px);
  .model-name {
    height: 56px;
    width: 100%;
    padding-left: 24px;
    border-bottom: 1px solid #1f232926;
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
    display: flex;
    align-items: center;
  }
  & > .ed-scrollbar {
    .form-content {
      width: 800px;
      margin: 0 auto;
      padding-top: 24px;
      height: 100%;
      padding-bottom: 80px;

      .ed-form-item--default {
        margin-bottom: 16px;

        &.is-error {
          margin-bottom: 40px;
        }
      }

      :deep(
        .custom-require.ed-form-item.is-required:not(.is-no-asterisk).asterisk-right
          > .ed-form-item__label:after
      ) {
        display: none;
      }

      :deep(.flex-inline .ed-form-item__label) {
        display: inline-flex;
        align-items: center;
      }

      .discovery-base-model {
        :deep(.ed-form-item__label) {
          position: relative;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: flex-start;
        }
        .discovery-button {
          position: absolute;
          top: 50%;
          right: 0;
          transform: translateY(-50%);
          .ed-icon {
            margin-right: 6px;
          }
          :deep(svg path) {
            fill: currentColor;
          }
        }
        .discovery-status-slot {
          width: 100%;
          height: 26px;
        }
        .discovery-status {
          font-size: 14px;
          line-height: 22px;
          margin-top: 4px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          &.success {
            color: #008a00;
          }
          &.empty {
            color: #6b7280;
          }
          &.error {
            color: #f00;
          }
        }
      }

      .enter {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #ff8800;
        margin-left: 8px;
      }

      .custom-require_danger::after {
        color: var(--ed-color-danger);
        content: '*';
        margin-left: 2px;
      }

      .advance-setting {
        display: flex;
        align-items: center;
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
        cursor: pointer;

        .ed-icon {
          margin-left: 8px;
        }

        &.expand {
          .ed-icon {
            transform: rotate(180deg);
          }
        }
      }

      .model-params {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        margin: 16px 0 8px 0;

        .btn {
          height: 26px;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0 4px;
          border-radius: 6px;
          cursor: pointer;

          &:hover {
            background-color: #1f23291a;
          }
        }

        .ed-icon {
          margin-right: 4px;
        }
      }

      .params-table {
        border-radius: 6px;
        border: 1px solid #dee0e3;
        border-top: none;
        border-bottom: none;
        overflow-y: auto;

        &.bottom-border {
          border-bottom: 1px solid #dee0e3;
        }
        :deep(.ed-table .ed-table__cell) {
          padding: 7px 0;
        }

        :deep(.ed-table .cell) {
          line-height: 24px;
        }
      }

      .params-table_pagination {
        margin-top: 8px;

        .ed-pagination {
          justify-content: flex-end;
        }

        :deep(.ed-pager li.number:hover) {
          background-color: var(--ed-color-primary-1a, #1cba901a);
        }
      }

      .operation-column_text {
        .ed-button {
          color: #646a73;
          height: 24px;
        }
        .ed-button:not(.is-disabled):hover {
          background: #1f23291a;
        }
        .ed-button + .ed-button {
          margin-left: 8px;
        }
      }
    }
  }

  &.is-edit_model {
    width: 100%;
    .form-content {
      padding-bottom: 24px;
    }
  }
}
.model-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}
.model-option-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.model-option-source {
  flex-shrink: 0;
  margin-left: 16px;
  font-size: 12px;
  font-weight: 400;
  color: var(--ed-text-color-secondary);
}
.discovery-select-hint {
  color: #6b7280;
  font-size: 14px;
  line-height: 22px;
}
</style>
<style lang="less">
.discovery-model-options {
  .ed-select-dropdown__wrap {
    max-height: 120px;
  }
  .ed-select-dropdown__item {
    height: 40px;
    line-height: 40px;
    font-size: 16px;
  }
  .ed-select-dropdown__item.is-selected {
    background: #e3efff;
    color: #0066ff;
  }
  .ed-select-dropdown__footer {
    padding: 8px 20px;
  }
}
</style>
