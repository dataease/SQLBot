<template>
  <div class="table-list_layout">
    <div class="header">
      <div class="title">
        <el-button text style="color: #fff" :icon="ArrowLeft" @click="back()" />
        {{ props.dsName }}
      </div>
    </div>
    <div class="container">
      <div class="left-side">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ t('ds.tables') }}</span>
          <el-button style="padding: 12px" text :icon="CreditCard" @click="editTables(ds)" />
        </div>
        <el-input
          v-model="searchValue"
          clearable
          style="margin: 16px 0"
          :placeholder="t('ds.Search Datasource')"
        />
        <div>
          <div
            v-for="(item, _index) in tableList"
            :key="_index"
            class="list-item_primary"
            @click="clickTable(item)"
          >
            {{ item.table_name }}
          </div>
        </div>
      </div>
      <div class="right-side">
        <div v-if="fieldList.length === 0">
          {{ t('ds.no_data_tip') }}
        </div>
        <div v-else>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div style="display: flex; justify-content: start; align-items: center">
              <span>{{ currentTable.table_name }}</span>
              <el-divider direction="vertical" />
              <span>{{ t('ds.comment') }}:</span>
              <span>{{ currentTable.custom_comment }}</span>
              <el-button
                style="margin-left: 10px"
                text
                class="action-btn"
                :icon="IconOpeEdit"
                @click="editTable"
              />
            </div>
          </div>
          <el-tabs v-model="activeName" class="demo-tabs" @tab-click="handleClick">
            <el-tab-pane :label="t('ds.table_schema')" name="schema">
              <el-table :data="fieldList" style="width: 100%">
                <el-table-column prop="field_name" :label="t('ds.field.name')" width="180" />
                <el-table-column prop="field_type" :label="t('ds.field.type')" width="180" />
                <el-table-column prop="field_comment" :label="t('ds.field.comment')" />
                <el-table-column :label="t('ds.field.custom_comment')">
                  <template #default="scope">
                    <div class="field-comment">
                      <span>{{ scope.row.custom_comment }}</span>
                      <el-button
                        text
                        class="action-btn"
                        :icon="IconOpeEdit"
                        @click="editField(scope.row)"
                      />
                    </div>
                  </template>
                </el-table-column>
                <el-table-column :label="t('ds.field.status')" width="180">
                  <template #default="scope">
                    <div style="display: flex; align-items: center">
                      <el-switch
                        v-model="scope.row.checked"
                        size="small"
                        @change="changeStatus(scope.row)"
                      />
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane :label="t('ds.preview')" name="preview">
              <div style="margin: 16px 0">{{ t('ds.preview_tip') }}</div>
              <el-table :data="previewData.data" style="width: 100%; height: 600px">
                <el-table-column
                  v-for="(c, index) in previewData.fields"
                  :key="index"
                  :prop="c"
                  :label="c"
                />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="tableDialog"
      :title="t('ds.edit.table_comment')"
      width="600"
      :destroy-on-close="true"
      :close-on-click-modal="false"
      @closed="closeTable"
    >
      <div>{{ t('ds.edit.table_comment_label') }}</div>
      <el-input v-model="tableComment" clearable :rows="3" type="textarea" />
      <div style="display: flex; justify-content: flex-end; margin-top: 20px">
        <el-button secondary @click="closeTable">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveTable">{{ t('common.confirm') }}</el-button>
      </div>
    </el-dialog>

    <el-dialog
      v-model="fieldDialog"
      :title="t('ds.edit.field_comment')"
      width="600"
      :destroy-on-close="true"
      :close-on-click-modal="false"
      @closed="closeField"
    >
      <div>{{ t('ds.edit.field_comment_label') }}</div>
      <el-input v-model="fieldComment" clearable :rows="3" type="textarea" />
      <div style="display: flex; justify-content: flex-end; margin-top: 20px">
        <el-button secondary @click="closeField">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveField">{{ t('common.confirm') }}</el-button>
      </div>
    </el-dialog>
  </div>
  <DsForm ref="dsForm" @refresh="refresh" />
</template>

<script setup lang="tsx">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { datasourceApi } from '@/api/datasource'
import { onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import type { TabsPaneContext } from 'element-plus-secondary'
import IconOpeEdit from '@/assets/svg/operate/ope-edit.svg'
import { CreditCard } from '@element-plus/icons-vue'
import DsForm from './form.vue'

const props = defineProps({
  dsId: { type: [Number], required: true },
  dsName: { type: [String], required: true },
})

const { t } = useI18n()

// eslint-disable-next-line vue/no-dupe-keys
const dsId = ref<number>(0)
const searchValue = ref('')
const tableList = ref<any>([])
const currentTable = ref<any>({})
const currentField = ref<any>({})
const fieldList = ref<any>([])
const previewData = ref<any>({})

const activeName = ref('schema')
const tableDialog = ref<boolean>(false)
const fieldDialog = ref<boolean>(false)
const dsForm = ref()
const ds = ref<any>({})
const tableComment = ref('')
const fieldComment = ref('')

const buildData = () => {
  return { table: currentTable.value, fields: fieldList.value }
}

const back = () => {
  history.back()
}

// const save = () => {
//   datasourceApi.edit(buildData()).then(() => {
//     ElMessage({
//       message: "Save success",
//       type: "success",
//       showClose: true,
//     });
//   });
// };

const editTable = () => {
  tableComment.value = currentTable.value.custom_comment
  tableDialog.value = true
}

const closeTable = () => {
  tableDialog.value = false
}

const saveTable = () => {
  currentTable.value.custom_comment = tableComment.value
  datasourceApi.saveTable(currentTable.value).then(() => {
    closeTable()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}

const editField = (row: any) => {
  currentField.value = row
  fieldComment.value = currentField.value.custom_comment
  fieldDialog.value = true
}

const changeStatus = (row: any) => {
  currentField.value = row
  datasourceApi.saveField(currentField.value).then(() => {
    closeField()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}

const closeField = () => {
  fieldDialog.value = false
}

const saveField = () => {
  currentField.value.custom_comment = fieldComment.value
  datasourceApi.saveField(currentField.value).then(() => {
    closeField()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}

const clickTable = (table: any) => {
  currentTable.value = table
  datasourceApi.fieldList(table.ds_id, table.id).then((res) => {
    fieldList.value = res
    datasourceApi.previewData(dsId.value, buildData()).then((res) => {
      previewData.value = res
    })
  })
}

const handleClick = (tab: TabsPaneContext) => {
  if (tab.paneName === 'preview') {
    datasourceApi.previewData(dsId.value, buildData()).then((res) => {
      previewData.value = res
    })
  }
}

const editTables = (item: any) => {
  dsForm.value.open(item, true)
}

const refresh = () => {
  init()
}

const init = () => {
  dsId.value = props.dsId
  datasourceApi.getDs(dsId.value).then((res) => {
    ds.value = res
    fieldList.value = []
    datasourceApi.tableList(props.dsId).then((res) => {
      tableList.value = res
    })
  })
}

onMounted(() => {
  init()
})
</script>

<style lang="less" scoped>
.table-list_layout {
  width: 100%;
  height: 100%;
  .header {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    background: #050e21;
    box-shadow: 0 2px 4px #1f23291f;
  }
  .title {
    color: #fff;
    font-size: 16px;
    font-weight: 400;
    display: flex;
    align-items: center;
    width: 50%;
    position: relative;
  }
  .container {
    height: calc(100% - 56px);
    width: 100%;
    .left-side {
      width: 246px;
      height: 100%;
      float: left;
      border-right: 1px solid #ccc;
      padding: 24px;
    }

    .right-side {
      width: calc(100% - 246px);
      height: 100%;
      float: right;
      padding: 24px;
    }
  }
}

.field-comment {
  display: flex;
  align-items: center;

  .action-btn {
    margin-left: 10px;
  }
}
</style>
