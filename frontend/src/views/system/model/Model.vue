<script lang="ts" setup>
import { ref, computed, shallowRef, reactive, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import icon_admin_outlined from '@/assets/svg/icon_admin_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import ModelList from './ModelList.vue'
import ModelListSide from './ModelListSide.vue'
import ModelForm from './ModelForm.vue'
import { modelApi } from '@/api/system'
import Card from './Card.vue'
import { getModelTypeName } from '@/entity/CommonEntity.ts'
import { useI18n } from 'vue-i18n'
import { get_supplier } from '@/entity/supplier'
import { highlightKeyword } from '@/utils/xss'

interface Model {
  name: string
  model_type: string
  base_model: string
  id?: string
  default_model: boolean
  supplier: number
}

const { t } = useI18n()
const keywords = ref('')
const defaultModelKeywords = ref('')
const modelConfigvVisible = ref(false)
const searchLoading = ref(false)
const editModel = ref(false)
const activeStep = ref(0)
const activeName = ref('')
const activeNameI18nKey = ref('')
const activeType = ref('')
const modelFormRef = ref()
const cardRefs = ref<any[]>([])
const showCardError = ref(false) // if you don`t want card mask error, just change this to false
reactive({
  form: {
    id: '',
    name: '',
    model_type: 0,
    api_key: '',
    api_domain: '',
  },
  selectedIds: [],
})
const modelList = shallowRef([] as Model[])

const modelListWithSearch = computed(() => {
  if (!keywords.value) return modelList.value
  return modelList.value.filter((ele) =>
    ele.name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})
const beforeClose = () => {
  modelConfigvVisible.value = false
}
const defaultModelListWithSearch = computed(() => {
  let tempModelList = modelList.value
  if (defaultModelKeywords.value) {
    tempModelList = tempModelList.filter((ele) =>
      ele.name.toLowerCase().includes(defaultModelKeywords.value.toLowerCase())
    )
  }
  return tempModelList.map((item: any) => {
    item['supplier_item'] = get_supplier(item.supplier)
    return item
  })
})

const modelCheckHandler = async (item: any) => {
  const response = await modelApi.check(item)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let checkTimeout = false
  setTimeout(() => {
    checkTimeout = true
  }, 9000)
  let checkMsg = ''
  while (true) {
    if (checkTimeout) {
      break
    }
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).trim().split('\n')
    for (const line of lines) {
      const data = JSON.parse(line)
      if (data.error) {
        checkMsg += data.error
      } else if (data.content) {
        console.debug(data.content)
      }
    }
  }
  if (!checkMsg) {
    return
  }
  console.error(checkMsg)
  if (!showCardError.value) {
    ElMessage.error(checkMsg)
    return
  }
  nextTick(() => {
    const index = modelListWithSearch.value.findIndex((el: any) => el.id === item.id)
    if (index > -1) {
      const currentRef = cardRefs.value[index]
      currentRef?.showErrorMask(checkMsg)
    }
  })
}
const duplicateName = async (item: any) => {
  const res = await modelApi.queryAll()
  const names = res.filter((ele: any) => ele.id !== item.id).map((ele: any) => ele.name)
  if (names.includes(item.name)) {
    ElMessage.error(t('embedded.duplicate_name'))
    return
  }
  const param = {
    ...item,
  }
  if (!item.id) {
    modelApi.add(param).then(() => {
      beforeClose()
      search()
      ElMessage({
        type: 'success',
        message: t('workspace.add_successfully'),
      })
      modelCheckHandler(item)
    })
    return
  }
  modelApi.edit(param).then(() => {
    beforeClose()
    search()
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
    modelCheckHandler(item)
  })
}

const handleDefaultModelChange = (item: any) => {
  const current_default_node = modelList.value.find((ele: Model) => ele.default_model)
  if (current_default_node?.id === item.id) {
    return
  }
  ElMessageBox.confirm(t('model.system_default_model', { msg: item.name }), {
    confirmButtonType: 'primary',
    tip: t('model.operate_with_caution'),
    confirmButtonText: t('datasource.confirm'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (val: string) => {
      if (val === 'confirm') {
        modelApi.setDefault(item.id).then(() => {
          ElMessage.success(t('model.set_successfully'))
          search()
        })
      }
    },
  })
}

const formatKeywords = (item: string) => {
  // Use XSS-safe highlight function
  return highlightKeyword(item, defaultModelKeywords.value, 'isSearch')
}
const handleAddModel = () => {
  activeStep.value = 0
  editModel.value = false
  modelConfigvVisible.value = true
}
const handleEditModel = (row: any) => {
  activeStep.value = 1
  editModel.value = true
  activeType.value = row.supplier
  activeName.value = row.supplier_item.name
  activeNameI18nKey.value = row.supplier_item.i18nKey
  modelApi.query(row.id).then((res: any) => {
    modelConfigvVisible.value = true
    nextTick(() => {
      modelFormRef.value.initForm({ ...res })
    })
  })
}

const handleDefault = (row: any) => {
  if (row.default_model) return
  ElMessageBox.confirm(t('model.system_default_model', { msg: row.name }), {
    confirmButtonType: 'primary',
    tip: t('model.operate_with_caution'),
    confirmButtonText: t('datasource.confirm'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (val: string) => {
      if (val === 'confirm') {
        modelApi.setDefault(row.id).then(() => {
          ElMessage.success(t('model.set_successfully'))
          search()
        })
      }
    },
  })
}

const deleteHandler = (item: any) => {
  if (item.default_model) {
    ElMessageBox.confirm(t('model.del_default_tip', { msg: item.name }), {
      confirmButtonType: 'primary',
      tip: t('model.del_default_warn'),
      showConfirmButton: false,
      confirmButtonText: t('datasource.confirm'),
      cancelButtonText: t('datasource.got_it'),
      customClass: 'confirm-no_icon',
      autofocus: false,
      callback: (val: string) => {
        console.info(val)
      },
    })
    return
  }
  ElMessageBox.confirm(t('model.del_warn_tip', { msg: item.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (value: string) => {
      if (value === 'confirm') {
        modelApi.delete(item.id).then(() => {
          ElMessage({
            type: 'success',
            message: t('dashboard.delete_success'),
          })
          search()
        })
      }
    },
  })
}

const clickModel = (ele: any) => {
  activeStep.value = 1
  supplierChang(ele)
}

const supplierChang = (ele: any) => {
  activeName.value = ele.name
  activeNameI18nKey.value = ele.i18nKey
  nextTick(() => {
    modelFormRef.value.supplierChang({ ...ele })
  })
}

const cancel = () => {
  beforeClose()
}

const preStep = () => {
  activeStep.value = 0
}

const saveModel = () => {
  modelFormRef.value.submitModel()
}
const setCardRef = (el: any, index: number) => {
  if (el) {
    cardRefs.value[index] = el
  }
}
const search = () => {
  searchLoading.value = true
  modelApi
    .queryAll()
    .then((res: any) => {
      modelList.value = res
    })
    .finally(() => {
      searchLoading.value = false
    })
}
search()

const submit = (item: any) => {
  duplicateName(item)
}
</script>

<template>
  <div class="model-config no-padding">
    <div class="model-methods">
      <span class="title">{{ t('model.ai_model_configuration') }}</span>
      <div class="button-input">
        <el-input
          v-model="keywords"
          clearable
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('datasource.search')"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined class="svg-icon" />
            </el-icon>
          </template>
        </el-input>

        <el-popover popper-class="system-default_model" placement="bottom-end">
          <template #reference>
            <el-button secondary>
              <template #icon>
                <icon_admin_outlined></icon_admin_outlined>
              </template>
              {{ t('model.system_default_model_de') }}
            </el-button></template
          >
          <div class="popover">
            <el-input
              v-model="defaultModelKeywords"
              clearable
              style="width: 100%; margin-right: 12px"
              :placeholder="t('datasource.search_by_name')"
            >
              <template #prefix>
                <el-icon>
                  <icon_searchOutline_outlined class="svg-icon" />
                </el-icon>
              </template>
            </el-input>
            <div class="popover-content">
              <div
                v-for="ele in defaultModelListWithSearch"
                :key="ele.name"
                class="popover-item"
                :class="ele.default_model && 'isActive'"
                @click="handleDefaultModelChange(ele)"
              >
                <img :src="ele.supplier_item.icon" width="24px" height="24px" />
                <div class="model-name ellipsis" v-html="formatKeywords(ele.name)"></div>
                <el-icon size="16" class="done">
                  <icon_done_outlined></icon_done_outlined>
                </el-icon>
              </div>
              <div v-if="!defaultModelListWithSearch.length" class="popover-item empty">
                {{ t('model.relevant_results_found') }}
              </div>
            </div>
          </div>
        </el-popover>

        <el-button type="primary" @click="handleAddModel">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ t('model.add_model') }}
        </el-button>
      </div>
    </div>
    <EmptyBackground
      v-if="!!keywords && !modelListWithSearch.length"
      :description="$t('datasource.relevant_content_found')"
      img-type="tree"
    />
    <div v-else class="card-content">
      <el-row :gutter="16" class="w-full">
        <el-col
          v-for="(ele, index) in modelListWithSearch"
          :key="ele.id"
          :xs="24"
          :sm="12"
          :md="12"
          :lg="8"
          :xl="6"
          class="mb-16"
        >
          <card
            :id="ele.id"
            :ref="(el: any) => setCardRef(el, index)"
            :key="ele.id"
            :name="ele.name"
            :supplier="ele.supplier"
            :model-type="getModelTypeName(ele['model_type'])"
            :base-model="ele['base_model']"
            :is-default="ele['default_model']"
            @edit="handleEditModel(ele)"
            @del="deleteHandler"
            @default="handleDefault(ele)"
          ></card>
        </el-col>
      </el-row>
    </div>
    <template v-if="!keywords && !modelListWithSearch.length && !searchLoading">
      <EmptyBackground
        class="datasource-yet"
        :description="$t('common.no_model_yet')"
        img-type="noneWhite"
      />

      <div style="text-align: center; margin-top: -10px">
        <el-button type="primary" @click="handleAddModel">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ t('model.add_model') }}
        </el-button>
      </div>
    </template>
    <el-drawer
      v-model="modelConfigvVisible"
      :close-on-click-modal="false"
      size="calc(100% - 100px)"
      modal-class="model-drawer-fullscreen"
      direction="btt"
      destroy-on-close
      :before-close="beforeClose"
      :show-close="false"
    >
      <template #header="{ close }">
        <span style="white-space: nowrap">{{
          editModel ? $t('dashboard.edit') + $t('common.empty') + $t(activeNameI18nKey) : t('model.add_model')
        }}</span>
        <div v-if="!editModel" class="flex-center" style="width: 100%">
          <el-steps custom style="max-width: 500px; flex: 1" :active="activeStep" align-center>
            <el-step>
              <template #title> {{ t('model.select_supplier') }} </template>
            </el-step>
            <el-step>
              <template #title> {{ t('model.add_model') }} </template>
            </el-step>
          </el-steps>
        </div>
        <el-icon class="ed-dialog__headerbtn mrt" style="cursor: pointer" @click="close">
          <icon_close_outlined></icon_close_outlined>
        </el-icon>
      </template>
      <ModelList v-if="activeStep === 0" @click-model="clickModel"></ModelList>
      <ModelListSide
        v-if="activeStep === 1 && !editModel"
        :active-name="activeName"
        :active-type="activeType"
        @click-model="supplierChang"
      ></ModelListSide>
      <ModelForm
        v-if="activeStep === 1 && modelConfigvVisible"
        ref="modelFormRef"
        :active-name="activeName"
        :active-type="activeType"
        :edit-model="editModel"
        @submit="submit"
      ></ModelForm>
      <template v-if="activeStep !== 0" #footer>
        <el-button secondary @click="cancel"> {{ $t('common.cancel') }} </el-button>
        <el-button v-if="!editModel" secondary @click="preStep">
          {{ $t('ds.previous') }}
        </el-button>
        <el-button type="primary" @click="saveModel"> {{ $t('common.save') }} </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="less" scoped>
.model-config {
  height: calc(100% - 16px);
  padding: 16px 0 16px 0;

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
  }
  .model-methods {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding: 0 24px 0 24px;
    .title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }
  }

  .card-content {
    max-height: calc(100% - 40px);
    overflow-y: auto;
    padding: 0 8px 0 24px;

    .w-full {
      width: 100%;
    }

    .mb-16 {
      margin-bottom: 16px;
    }
  }
}
</style>

<style lang="less">
.system-default_model.system-default_model {
  padding: 4px 0;
  width: 325px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;
  .ed-input {
    .ed-input__wrapper {
      box-shadow: none;
    }

    border-bottom: 1px solid #1f232926;
  }

  .popover {
    .popover-content {
      padding: 4px;
      max-height: 300px;
      overflow-y: auto;
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      margin-bottom: 2px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      &:not(.empty):hover {
        background: #1f23291a;
      }

      &.empty {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #8f959e;
        cursor: default;
      }

      .model-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        max-width: 220px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      .isSearch {
        color: var(--ed-color-primary);
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}

.model-drawer-fullscreen {
  .ed-drawer__body {
    padding: 0;
  }
  .is-process .ed-step__line {
    background-color: var(--ed-color-primary);
  }
}
.confirm-no_icon {
  border-radius: 12px;
  padding: 24px;
  .tip {
    margin-top: 24px;
  }
}
</style>
