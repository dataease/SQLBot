<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_warning_filled from '@/assets/svg/icon_info_colorful.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_visible_outlined_blod from '@/assets/embedded/icon_visible_outlined_blod.svg'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_invisible_outlined from '@/assets/embedded/icon_invisible_outlined.svg'
import icon_visible_outlined from '@/assets/embedded/icon_visible_outlined.svg'
import { formatTimestamp } from '@/utils/date'
import { useClipboard } from '@vueuse/core'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { request } from '@/utils/request'

const { t } = useI18n()

const limitCount = ref(5)
const limitValid = ref(true)

const triggerLimit = computed(() => {
  return limitValid.value && state.tableData.length >= limitCount.value
})
const state = reactive({
  tableData: [] as any,
})

const handleAdd = () => {
  if (triggerLimit.value) {
    return
  }
  request.post('/system/apikey', {}).then(() => {
    loadGridData()
  })
}
const pwd = ref('**********')
const toApiDoc = () => {
  console.log('Add API Key')
  const url = '/docs'
  window.open(url, '_blank')
}

const statusHandler = (row: any) => {
  const param = {
    id: row.id,
    status: row.status,
  }
  request.put('/system/apikey/status', param).then(() => {
    loadGridData()
  })
}
const { copy } = useClipboard({ legacy: true })

const copyCode = (row: any, key: any = 'secret_key') => {
  copy(row[key])
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
const deleteHandler = (row: any) => {
  ElMessageBox.confirm(t('user.del_key', { msg: row.access_key }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (action: any) => {
      if (action === 'confirm') {
        request.delete(`/system/apikey/${row.id}`).then(() => {
          loadGridData()
          ElMessage({
            type: 'success',
            message: t('dashboard.delete_success'),
          })
        })
      }
    },
  })
}
const sortChange = (param: any) => {
  if (param?.order === 'ascending') {
    state.tableData.sort((a: any, b: any) => a.create_time - b.create_time)
  } else {
    state.tableData.sort((a: any, b: any) => b.create_time - a.create_time)
  }
}
const loadGridData = () => {
  request.get('/system/apikey').then((res: any) => {
    state.tableData = res || []
  })
}
onMounted(() => {
  loadGridData()
})
</script>

<template>
  <div class="sqlbot-apikey-container">
    <div class="warn-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="warn-template-content">
        <span>{{ t('api_key.info_tips') }}</span>
      </div>
    </div>

    <div class="api-key-btn">
      <el-tooltip
        v-if="triggerLimit"
        :offset="14"
        effect="dark"
        :content="t('api_key.trigger_limit', [limitCount])"
        placement="top"
      >
        <el-button v-if="triggerLimit" type="info" disabled>
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('api_key.create') }}
        </el-button>
      </el-tooltip>
      <el-button v-else type="primary" @click="handleAdd">
        <template #icon>
          <icon_add_outlined></icon_add_outlined>
        </template>
        {{ $t('api_key.create') }}
      </el-button>

      <el-button secondary @click="toApiDoc">
        <template #icon>
          <icon_visible_outlined_blod></icon_visible_outlined_blod>
        </template>
        {{ $t('api_key.to_doc') }}
      </el-button>
    </div>
    <div class="api-key-grid">
      <el-table
        ref="multipleTableRef"
        :data="state.tableData"
        style="width: 100%"
        @sort-change="sortChange"
      >
        <el-table-column prop="access_key" label="Access Key" width="206">
          <template #default="scope">
            <div class="user-status-container">
              <div :title="scope.row.access_key" class="ellipsis" style="max-width: 208px">
                {{ scope.row.access_key }}
              </div>
              <el-tooltip
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon
                  size="16"
                  class="hover-icon_with_bg"
                  @click="copyCode(scope.row, 'access_key')"
                >
                  <icon_copy_outlined></icon_copy_outlined>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="secret_key" label="Secret Key" width="206">
          <template #default="scope">
            <div class="user-status-container">
              <div
                :title="scope.row.showPwd ? scope.row.secret_key : pwd"
                class="ellipsis"
                style="max-width: 208px"
              >
                {{ scope.row.showPwd ? scope.row.secret_key : pwd }}
              </div>
              <el-tooltip
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="copyCode(scope.row)">
                  <icon_copy_outlined></icon_copy_outlined>
                </el-icon>
              </el-tooltip>

              <el-tooltip
                v-if="scope.row.showPwd"
                :offset="12"
                effect="dark"
                :content="t('embedded.click_to_hide')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = false">
                  <icon_visible_outlined></icon_visible_outlined>
                </el-icon>
              </el-tooltip>

              <el-tooltip
                v-if="!scope.row.showPwd"
                :offset="12"
                effect="dark"
                :content="t('embedded.click_to_show')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = true">
                  <icon_invisible_outlined></icon_invisible_outlined>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" width="100" :label="t('datasource.enabled_status')">
          <template #default="scope">
            <div class="api-status-container" :class="[scope.row.status ? 'active' : 'disabled']">
              <el-icon size="16">
                <SuccessFilled v-if="scope.row.status" />
                <CircleCloseFilled v-else />
              </el-icon>
              <span>{{ $t(`user.${scope.row.status ? 'enabled' : 'disabled'}`) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" width="180" sortable :label="t('user.creation_time')">
          <template #default="scope">
            <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
          </template>
        </el-table-column>
        <el-table-column fixed="right" width="100" :label="$t('ds.actions')">
          <template #default="scope">
            <div class="table-operate">
              <el-switch
                v-model="scope.row.status"
                :active-value="true"
                :inactive-value="false"
                size="small"
                @change="statusHandler(scope.row)"
              />
              <div class="line"></div>
              <el-tooltip
                :offset="14"
                effect="dark"
                :content="$t('dashboard.delete')"
                placement="top"
              >
                <el-icon class="action-btn" size="16" @click="deleteHandler(scope.row)">
                  <IconOpeDelete></IconOpeDelete>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyBackground
            v-if="!state.tableData.length"
            :description="$t('datasource.relevant_content_found')"
            img-type="none"
          />
        </template>
      </el-table>
    </div>
  </div>
</template>

<style lang="less" scoped>
.sqlbot-apikey-container {
  background: #ffffff;
  border-radius: 8px;
  row-gap: 24px;
  display: flex;
  flex-direction: column;

  .warn-template {
    display: flex;
    align-items: center;
    background: #d2f1e9;
    // border: 1px solid #ffe7ba;
    border-radius: 6px;
    padding: 9px 16px;

    .icon-span {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      display: flex;
      align-items: center;
      margin-top: -20px;
      i {
        width: 16px;
        height: 16px;
      }

      .svg-icon {
        width: 16px;
        height: 16px;
      }
    }

    .warn-template-content {
      font-size: 14px;
      color: #1f2329;
    }
  }

  .api-key-btn {
    margin-bottom: 0px;

    .el-button {
      margin-right: 8px;
    }
  }

  .api-key-grid {
    width: 100%;
    .el-table {
      width: 100%;
    }

    .table-operate {
      display: flex;
      align-items: center;

      .line {
        width: 1px;
        height: 16px;
        background: #e8e8e8;
        margin: 0 12px;
      }

      .action-btn {
        width: 24px;
        height: 24px;
        border-radius: 6px;
        cursor: pointer;
        color: #646a73;

        &:hover {
          background-color: #1f23291a;
        }
      }
    }
    .api-status-container {
      display: flex;
      align-items: center;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;

      .ed-icon {
        margin-right: 8px;
      }
    }
    .user-status-container {
      display: flex;
      align-items: center;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      height: 24px;

      .ed-icon {
        margin-left: 8px;
      }

      .ed-icon + .ed-icon {
        margin-left: 12px;
      }
    }
  }
}
</style>
