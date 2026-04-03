<script setup lang="ts">
import { ref, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'
import SheetTabs from './SheetTabs.vue'
import field_text from '@/assets/svg/field_text.svg'
import field_time from '@/assets/svg/field_time.svg'
import field_value from '@/assets/svg/field_value.svg'
import { datasourceApi } from '@/api/datasource'

const { t } = useI18n()

const emits = defineEmits(['finish'])
const tabList = shallowRef([])
const fieldList = shallowRef([])
const iconMap = {
  string: field_text,
  int: field_value,
  float: field_value,
  datetime: field_time,
}
const dialogShow = ref(false)
const loading = ref(false)
const previewData = ref<any>({})

const variables = [
  {
    name: t('model.text'),
    var_type: 'string',
  },
  {
    name: t('model.int'),
    var_type: 'int',
  },
  {
    name: t('model.float'),
    var_type: 'float',
  },
  {
    name: t('dashboard.time'),
    var_type: 'datetime',
  },
]

let arr: any = []
let filePath = ''
const init = (response: any) => {
  arr = response.data || []
  filePath = response.filePath
  previewData.value = response.data[0]
  activeTab.value = previewData.value.sheetName
  fieldList.value = previewData.value.fields
  tabList.value = response.data.map((item: any) => {
    return {
      label: item.sheetName,
      value: item.sheetName,
    }
  })
  dialogShow.value = true
}

const closeDialog = () => {
  arr = []
  previewData.value = {
    sheetName: '',
    fields: [],
    data: [],
    rows: 0,
  }
  tabList.value = []
  fieldList.value = []
  activeTab.value = ''
  btnSelect.value = 'd'
  dialogShow.value = false
}

const save = () => {
  loading.value = true
  datasourceApi
    .importToDb({
      sheets: arr.map((item: any) => {
        return { fields: item.fields, sheetName: item.sheetName }
      }),
      filePath,
    })
    .then((res: any) => {
      closeDialog()
      emits('finish', res)
    })
    .finally(() => {
      loading.value = false
    })
}
const btnSelect = ref('d')
const btnSelectClick = (val: any) => {
  btnSelect.value = val
}
const activeTab = ref('')
const handleTabClick = (tab: any) => {
  btnSelectClick('d')
  activeTab.value = tab.value
  arr.forEach((item: any) => {
    if (item.sheetName === activeTab.value) {
      previewData.value = item
    }
  })
  fieldList.value = previewData.value.fields
}

const renderHeader = ({ column }: any) => {
  //创建一个元素用于存放表头信息
  const span = document.createElement('span')
  // 将表头信息渲染到元素上
  span.innerText = column.label
  // 在界面中添加该元素
  document.body.appendChild(span)
  //获取该元素的宽度（包含内外边距等信息）
  const spanWidth = span.getBoundingClientRect().width + 20 //渲染后的 div 内左右 padding 都是 10，所以 +20
  //判断是否小于element的最小宽度，两者取最大值
  column.minWidth = column.minWidth > spanWidth ? column.minWidth : spanWidth
  // 计算完成后，删除该元素
  document.body.removeChild(span)
  return column.label
}

defineExpose({
  init,
})
</script>

<template>
  <el-dialog
    v-model="dialogShow"
    :title="$t('ds.preview')"
    width="1200"
    modal-class="excel-detail-dialog"
    destroy-on-close
    :close-on-click-modal="false"
    @before-closed="closeDialog"
  >
    <SheetTabs :active-tab="activeTab" :tab-list="tabList" @tab-click="handleTabClick"></SheetTabs>
    <div v-loading="loading" class="content">
      <div class="btn-select" style="margin: 8px 12px">
        <el-button :class="[btnSelect === 'd' && 'is-active']" text @click="btnSelectClick('d')">
          {{ t('ds.preview') }}
        </el-button>
        <el-button :class="[btnSelect === 'q' && 'is-active']" text @click="btnSelectClick('q')">
          {{ t('sync.field_details') }}
        </el-button>
      </div>
      <div class="preview-num">
        {{ t('sync.records', { num: previewData.data.length, total: previewData.rows }) }}
      </div>

      <div v-if="btnSelect === 'q'" class="field-details">
        <el-table row-class-name="hover-icon_edit" :data="fieldList" style="width: 100%">
          <el-table-column prop="fieldName" :label="t('datasource.field_name')" />
          <el-table-column prop="fieldType" :label="t('datasource.field_type')" width="240">
            <template #default="scope">
              <el-icon
                :class="`${scope.row.fieldType}-variables`"
                size="16"
                style="position: absolute; top: 20px; left: 32px; z-index: 10"
              >
                <component :is="iconMap[scope.row.fieldType as keyof typeof iconMap]"></component>
              </el-icon>
              <el-select
                v-model="scope.row.fieldType"
                style="max-width: 197px; margin-left: 8px"
                :placeholder="t('datasource.Please_select')"
              >
                <el-option
                  v-for="ele in variables"
                  :key="ele.var_type"
                  :label="ele.name"
                  :value="ele.var_type"
                >
                  <div style="width: 100%; display: flex; align-items: center">
                    <el-icon
                      :class="`${ele.var_type}-variables`"
                      size="16"
                      style="margin-right: 4px"
                    >
                      <component :is="iconMap[ele.var_type as keyof typeof iconMap]"></component>
                    </el-icon>
                    {{ ele.name }}
                  </div>
                </el-option>
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="preview">
        <div class="table-container">
          <el-table :data="previewData.data" style="width: 100%; height: 100%">
            <el-table-column
              v-for="(c, index) in previewData.fields"
              :key="index"
              :prop="c.fieldName"
              :label="c.fieldName"
              min-width="150"
              :render-header="renderHeader"
            />
          </el-table>
        </div>
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeDialog">{{ $t('common.cancel') }}</el-button>
      <el-button v-loading="loading" type="primary" @click="save">{{
        $t('sync.confirm_upload')
      }}</el-button>
    </div>
  </el-dialog>
</template>

<style lang="less">
.excel-detail-dialog {
  .content {
    height: 593px;
    background-color: #f5f6f7;
    border: 1px solid #dee0e3;
    border-radius: 6px;
    margin-top: -1px;
    border-top-left-radius: 0;
    position: relative;
    z-index: 1;
    .field-details {
      .ed-select__wrapper {
        padding-left: 32px;
      }
    }
    .btn-select {
      height: 32px;
      padding-left: 4px;
      padding-right: 4px;
      display: inline-flex;
      background: #ffffff;
      align-items: center;
      border: 1px solid #d0d3d6;
      border-radius: 6px;

      .is-active {
        background: var(--ed-color-primary-1a, #1cba901a);
      }

      .ed-button:not(.is-active) {
        color: #1f2329;
      }
      .ed-button.is-text {
        height: 24px;
        width: auto;
        padding: 0 8px;
        line-height: 24px;
      }
      .ed-button + .ed-button {
        margin-left: 4px;
      }
    }

    .preview-num {
      margin: 0 0 8px 12px;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      color: #646a73;
    }

    .table-container {
      width: 100%;
      height: calc(100% - 46px);
    }
  }
}
</style>
