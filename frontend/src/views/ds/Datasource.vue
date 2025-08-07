<script lang="ts" setup>
import { ref, computed, shallowRef, nextTick, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import arrow_down from '@/assets/svg/arrow-down.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useRouter } from 'vue-router'
import DataTable from './DataTable.vue'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import DatasourceList from './DatasourceList.vue'
import DatasourceListSide from './DatasourceListSide.vue'
import DatasourceForm from './DatasourceForm.vue'
import { datasourceApi } from '@/api/datasource'
import Card from './Card.vue'
import DelMessageBox from './DelMessageBox.vue'
import { dsTypeWithImg } from './js/ds-type'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { chatApi } from '@/api/chat'
const userStore = useUserStore()
interface Datasource {
  name: string
  num: string
  type_name: string
  type: string
  img: string
  description: string
  id?: string
}

const router = useRouter()
const { t } = useI18n()
const keywords = ref('')
const defaultDatasourceKeywords = ref('')
const datasourceConfigVisible = ref(false)
const editDatasource = ref(false)
const activeStep = ref(0)
const activeName = ref('')
const activeType = ref('')
const datasourceFormRef = ref()
const searchLoading = ref(false)

const datasourceList = shallowRef([] as Datasource[])
const defaultDatasourceList = shallowRef(dsTypeWithImg as (Datasource & { img: string })[])

const currentDefaultDatasource = ref('')
const datasourceListWithSearch = computed(() => {
  if (!keywords.value && !currentDatasourceType.value) return datasourceList.value
  return datasourceList.value.filter(
    (ele) =>
      ele.name.toLowerCase().includes(keywords.value.toLowerCase()) &&
      (ele.type === currentDatasourceType.value || !currentDatasourceType.value)
  )
})
const beforeClose = () => {
  datasourceConfigVisible.value = false
  activeStep.value = 0
  datasourceApi.cancelRequests()
}
const defaultDatasourceListWithSearch = computed(() => {
  if (!defaultDatasourceKeywords.value) return defaultDatasourceList.value
  return defaultDatasourceList.value.filter((ele) =>
    ele.name.toLowerCase().includes(defaultDatasourceKeywords.value.toLowerCase())
  )
})

const currentDatasourceType = ref('')

const handleDefaultDatasourceChange = (item: any) => {
  if (currentDatasourceType.value === item.type) {
    currentDefaultDatasource.value = ''
    currentDatasourceType.value = ''
  } else {
    currentDefaultDatasource.value = item.name
    currentDatasourceType.value = item.type
  }
}

const changeActiveStep = (val: number) => {
  activeStep.value = val > 2 ? 2 : val
}

const formatKeywords = (item: string) => {
  if (!defaultDatasourceKeywords.value) return item
  return item.replaceAll(
    defaultDatasourceKeywords.value,
    `<span class="isSearch">${defaultDatasourceKeywords.value}</span>`
  )
}
const currentType = ref('')
const handleEditDatasource = (res: any) => {
  activeStep.value = 1
  datasourceConfigVisible.value = true
  editDatasource.value = true
  currentType.value = res.type_name
  nextTick(() => {
    datasourceFormRef.value.initForm(res)
  })
}

const handleQuestion = async (id: string) => {
  try {
    await chatApi.checkLLMModel()
  } catch (error: any) {
    console.error(error)
    let errorMsg = t('model.default_miss')
    let confirm_text = t('datasource.got_it')
    if (userStore.isAdmin) {
      errorMsg = t('model.default_miss_admin')
      confirm_text = t('model.to_config')
    }
    ElMessageBox.confirm(t('qa.ask_failed'), {
      confirmButtonType: 'primary',
      tip: errorMsg,
      showCancelButton: userStore.isAdmin,
      confirmButtonText: confirm_text,
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
      showClose: false,
      callback: (val: string) => {
        if (userStore.isAdmin && val === 'confirm') {
          router.push('/system/model')
        }
      },
    })
    return
  }
  router.push({
    path: '/chat/index',
    query: {
      start_chat: id,
    },
  })
}

const handleAddDatasource = () => {
  editDatasource.value = false
  datasourceConfigVisible.value = true
}

const refresh = () => {
  activeName.value = ''
  activeStep.value = 0
  activeType.value = ''
  datasourceConfigVisible.value = false
  search()
}

const refreshData = () => {
  search()
}

const panelClick = () => {
  console.info('panelClick')
}

const smartClick = () => {
  console.info('smartClick')
}

const deleteHandler = (item: any) => {
  ElMessageBox.confirm('', {
    confirmButtonType: 'danger',
    tip: t('datasource.operate_with_caution'),
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    dangerouslyUseHTMLString: true,
    message: h(
      DelMessageBox,
      {
        name: item.name,
        panelNum: 1,
        smartNum: 4,
        onPanelClick: panelClick,
        onSmartClick: smartClick,
        t,
      },
      ''
    ),
  }).then(() => {
    datasourceApi.delete(item.id).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
  // .catch(() => {
  //   ElMessageBox.confirm(t('datasource.data_source_de', { msg: item.name }), {
  //     tip: t('datasource.cannot_be_deleted'),
  //     cancelButtonText: t('datasource.got_it'),
  //     showConfirmButton: false,
  //     customClass: 'confirm-no_icon',
  //     autofocus: false,
  //   })
  // })
}

const clickDatasource = (ele: any) => {
  activeStep.value = 1
  activeName.value = ele.name
  activeType.value = ele.type
}

const clickDatasourceSide = (ele: any) => {
  activeName.value = ele.name
  activeType.value = ele.type
}

const search = () => {
  searchLoading.value = true
  datasourceApi
    .list()
    .then((res: any) => {
      datasourceList.value = res
    })
    .finally(() => {
      searchLoading.value = false
    })
}
search()

const currentDataTable = ref()
const dataTableDetail = (ele: any) => {
  currentDataTable.value = ele
}

const back = () => {
  currentDataTable.value = null
}
</script>

<template>
  <div v-show="!currentDataTable" class="datasource-config no-padding">
    <div class="datasource-methods">
      <span class="title">{{ $t('ds.title') }}</span>
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

        <el-popover popper-class="system-default_datasource" placement="bottom-end">
          <template #reference>
            <el-button secondary>
              {{ currentDefaultDatasource || $t('datasource.all_types') }}
              <el-icon style="margin-left: 8px">
                <arrow_down></arrow_down>
              </el-icon> </el-button
          ></template>
          <div class="popover">
            <el-input
              v-model="defaultDatasourceKeywords"
              clearable
              style="width: 100%; margin-right: 12px"
              :placeholder="$t('datasource.search_by_name')"
            >
              <template #prefix>
                <el-icon>
                  <icon_searchOutline_outlined class="svg-icon" />
                </el-icon>
              </template>
            </el-input>
            <div class="popover-content">
              <div
                v-for="ele in defaultDatasourceListWithSearch"
                :key="ele.name"
                class="popover-item"
                :class="currentDefaultDatasource === ele.name && 'isActive'"
                @click="handleDefaultDatasourceChange(ele)"
              >
                <img :src="ele.img" width="24px" height="24px" />
                <div class="datasource-name" v-html="formatKeywords(ele.name)"></div>
                <el-icon size="16" class="done">
                  <icon_done_outlined></icon_done_outlined>
                </el-icon>
              </div>
              <div v-if="!defaultDatasourceListWithSearch.length" class="popover-item empty">
                {{ t('model.relevant_results_found') }}
              </div>
            </div>
          </div>
        </el-popover>

        <el-button type="primary" @click="handleAddDatasource">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('datasource.new_data_source') }}
        </el-button>
      </div>
    </div>
    <EmptyBackground
      v-if="!!keywords && !datasourceListWithSearch.length"
      :description="$t('datasource.relevant_content_found')"
      class="datasource-yet"
      img-type="tree"
    />

    <div v-else class="card-content">
      <el-row :gutter="16" class="w-full">
        <el-col
          v-for="ele in datasourceListWithSearch"
          :key="ele.id"
          :xs="24"
          :sm="12"
          :md="12"
          :lg="8"
          :xl="6"
          class="mb-16"
        >
          <Card
            :id="ele.id"
            :key="ele.id"
            :name="ele.name"
            :type="ele.type"
            :type-name="ele.type_name"
            :num="ele.num"
            :description="ele.description"
            @question="handleQuestion"
            @edit="handleEditDatasource(ele)"
            @del="deleteHandler(ele)"
            @data-table-detail="dataTableDetail(ele)"
          ></Card>
        </el-col>
      </el-row>
    </div>
    <template v-if="!keywords && !datasourceListWithSearch.length && !searchLoading">
      <EmptyBackground
        class="datasource-yet"
        :description="$t('datasource.data_source_yet')"
        img-type="noneWhite"
      />

      <div style="text-align: center; margin-top: -10px">
        <el-button type="primary" @click="handleAddDatasource">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('datasource.new_data_source') }}
        </el-button>
      </div>
    </template>
    <el-drawer
      v-model="datasourceConfigVisible"
      :close-on-click-modal="false"
      size="calc(100% - 100px)"
      modal-class="datasource-drawer-fullscreen"
      direction="btt"
      :before-close="beforeClose"
      :show-close="false"
    >
      <template #header="{ close }">
        <span style="white-space: nowrap">{{
          editDatasource
            ? t('datasource.mysql_data_source', { msg: currentType })
            : $t('datasource.new_data_source')
        }}</span>
        <div v-if="!editDatasource" class="flex-center" style="width: 100%">
          <el-steps custom style="max-width: 800px; flex: 1" :active="activeStep" align-center>
            <el-step>
              <template #title> {{ $t('qa.select_datasource') }} </template>
            </el-step>
            <el-step>
              <template #title> {{ $t('datasource.configuration_information') }} </template>
            </el-step>
            <el-step>
              <template #title> {{ $t('ds.form.choose_tables') }} </template>
            </el-step>
          </el-steps>
        </div>
        <el-icon style="cursor: pointer" @click="close">
          <icon_close_outlined></icon_close_outlined>
        </el-icon>
      </template>
      <DatasourceList v-if="activeStep === 0" @click-datasource="clickDatasource"></DatasourceList>
      <DatasourceListSide
        v-if="activeStep === 1 && !editDatasource"
        :active-name="activeName"
        @click-datasource="clickDatasourceSide"
      ></DatasourceListSide>
      <DatasourceForm
        v-if="[1, 2].includes(activeStep)"
        ref="datasourceFormRef"
        :is-data-table="false"
        :active-step="activeStep"
        :active-name="activeName"
        :active-type="activeType"
        @refresh="refresh"
        @close="beforeClose"
        @change-active-step="changeActiveStep"
      ></DatasourceForm>
    </el-drawer>
  </div>
  <DataTable
    v-if="currentDataTable"
    :info="currentDataTable"
    @refresh="refreshData"
    @back="back"
  ></DataTable>
</template>

<style lang="less" scoped>
.datasource-config {
  height: calc(100% - 16px);
  padding: 16px 0 16px 0;
  .datasource-methods {
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

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
  }
}
</style>

<style lang="less">
.system-default_datasource.system-default_datasource {
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

      .datasource-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
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

.datasource-drawer-fullscreen {
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
