<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClipboard } from '@vueuse/core'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_warning_filled from '@/assets/svg/icon_info_colorful.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { formatTimestamp } from '@/utils/date'
import { datasourceApi } from '@/api/datasource'
import { agentTokenApi, type AgentToken } from '@/api/agentToken'

interface DatasourceOption {
  id: string
  name: string
}

const MAX_TOKENS = 5
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })

const state = reactive({
  tokens: [] as AgentToken[],
  datasources: [] as DatasourceOption[],
})
const createVisible = ref(false)
const creating = ref(false)
const form = reactive({ name: '', restrict: false, datasourceIds: [] as string[] })
// Shown once after creation; cleared when the dialog closes.
const issuedToken = ref('')

const limitReached = computed(() => state.tokens.length >= MAX_TOKENS)
const mcpUrl = computed(
  () => `${window.location.protocol}//${window.location.hostname}:8001/sqlbot-mcp`
)
const claudeCommand = computed(
  () =>
    `claude mcp add --transport http sqlbot-mcp ${mcpUrl.value} --header "Authorization: Bearer ${issuedToken.value || '<token>'}"`
)
const datasourceName = (id: string) => state.datasources.find((d) => d.id === id)?.name || id

const loadTokens = () => {
  agentTokenApi.list().then((res) => {
    state.tokens = res || []
  })
}
const loadDatasources = () => {
  datasourceApi.list().then((res: any) => {
    state.datasources = (res || []).map((d: any) => ({ id: String(d.id), name: d.name }))
  })
}

const openCreate = () => {
  if (limitReached.value) return
  form.name = ''
  form.restrict = false
  form.datasourceIds = []
  issuedToken.value = ''
  createVisible.value = true
}

const submitCreate = () => {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning(t('agent_token.name_required'))
    return
  }
  if (form.restrict && !form.datasourceIds.length) {
    ElMessage.warning(t('agent_token.datasource_required'))
    return
  }
  creating.value = true
  agentTokenApi
    .create({ name, datasource_ids: form.restrict ? form.datasourceIds : null })
    .then((res) => {
      issuedToken.value = res.token
      loadTokens()
    })
    .finally(() => {
      creating.value = false
    })
}

const closeCreate = () => {
  issuedToken.value = ''
  createVisible.value = false
}

const copyText = (text: string) => {
  copy(text)
    .then(() => ElMessage.success(t('embedded.copy_successful')))
    .catch(() => ElMessage.error(t('embedded.copy_failed')))
}

const toggleStatus = (row: AgentToken) => {
  agentTokenApi.setStatus(row.id, row.status).finally(loadTokens)
}

const removeToken = (row: AgentToken) => {
  ElMessageBox.confirm(t('agent_token.delete_confirm', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (action: any) => {
      if (action !== 'confirm') return
      agentTokenApi.remove(row.id).then(() => {
        loadTokens()
        ElMessage.success(t('dashboard.delete_success'))
      })
    },
  })
}

onMounted(() => {
  loadTokens()
  loadDatasources()
})
</script>

<template>
  <div class="sqlbot-agent-token-container">
    <div class="warn-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="warn-template-content">
        <span>{{ t('agent_token.info_tips') }}</span>
      </div>
    </div>

    <div class="agent-token-btn">
      <el-tooltip
        v-if="limitReached"
        :offset="14"
        effect="dark"
        :content="t('agent_token.trigger_limit', [MAX_TOKENS])"
        placement="top"
      >
        <el-button type="info" disabled>
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ t('agent_token.create') }}
        </el-button>
      </el-tooltip>
      <el-button v-else type="primary" @click="openCreate">
        <template #icon>
          <icon_add_outlined></icon_add_outlined>
        </template>
        {{ t('agent_token.create') }}
      </el-button>
    </div>

    <el-table :data="state.tokens" style="width: 100%">
      <el-table-column prop="name" :label="t('agent_token.name')" min-width="120">
        <template #default="scope">
          <div :title="scope.row.name" class="ellipsis">{{ scope.row.name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="token_prefix" :label="t('agent_token.token')" width="190">
        <template #default="scope">
          <span class="mono">{{ scope.row.token_prefix }}-••••</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('agent_token.scope')" min-width="140">
        <template #default="scope">
          <span v-if="scope.row.datasource_ids === null">{{ t('agent_token.scope_all') }}</span>
          <span
            v-else
            class="ellipsis"
            :title="scope.row.datasource_ids.map(datasourceName).join(', ')"
          >
            {{ scope.row.datasource_ids.map(datasourceName).join(', ') }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="status" width="100" :label="t('datasource.enabled_status')">
        <template #default="scope">
          <div class="token-status" :class="[scope.row.status ? 'active' : 'disabled']">
            <el-icon size="16">
              <SuccessFilled v-if="scope.row.status" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>{{ t(`user.${scope.row.status ? 'enabled' : 'disabled'}`) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="t('agent_token.last_used')" width="170">
        <template #default="scope">
          <span v-if="scope.row.last_used_time">
            {{ formatTimestamp(scope.row.last_used_time, 'YYYY-MM-DD HH:mm:ss') }}
          </span>
          <span v-else class="muted">{{ t('agent_token.never_used') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" width="170" :label="t('user.creation_time')">
        <template #default="scope">
          <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
        </template>
      </el-table-column>
      <el-table-column fixed="right" width="100" :label="t('ds.actions')">
        <template #default="scope">
          <div class="table-operate">
            <el-switch
              v-model="scope.row.status"
              :active-value="true"
              :inactive-value="false"
              size="small"
              @change="toggleStatus(scope.row)"
            />
            <div class="line"></div>
            <el-tooltip :offset="14" effect="dark" :content="t('dashboard.delete')" placement="top">
              <el-icon class="action-btn" size="16" @click="removeToken(scope.row)">
                <IconOpeDelete></IconOpeDelete>
              </el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
      <template #empty>
        <EmptyBackground
          v-if="!state.tokens.length"
          :description="t('datasource.relevant_content_found')"
          img-type="none"
        />
      </template>
    </el-table>

    <el-dialog
      v-model="createVisible"
      :title="issuedToken ? t('agent_token.created_title') : t('agent_token.create')"
      width="600"
      append-to-body
      :close-on-click-modal="false"
      @closed="issuedToken = ''"
    >
      <template v-if="!issuedToken">
        <el-form label-position="top" @submit.prevent>
          <el-form-item :label="t('agent_token.name')" required>
            <el-input
              v-model="form.name"
              maxlength="64"
              show-word-limit
              :placeholder="t('agent_token.name_placeholder')"
            />
          </el-form-item>
          <el-form-item :label="t('agent_token.scope')">
            <el-radio-group v-model="form.restrict">
              <el-radio :value="false">{{ t('agent_token.scope_all') }}</el-radio>
              <el-radio :value="true">{{ t('agent_token.scope_selected') }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.restrict">
            <el-select
              v-model="form.datasourceIds"
              multiple
              filterable
              style="width: 100%"
              :placeholder="t('agent_token.datasource_placeholder')"
            >
              <el-option
                v-for="ds in state.datasources"
                :key="ds.id"
                :label="ds.name"
                :value="ds.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </template>
      <template v-else>
        <div class="issued">
          <div class="issued-tip">{{ t('agent_token.created_tip') }}</div>
          <div class="issued-row">
            <code class="mono issued-value">{{ issuedToken }}</code>
            <el-icon class="hover-icon_with_bg" size="16" @click="copyText(issuedToken)">
              <icon_copy_outlined></icon_copy_outlined>
            </el-icon>
          </div>
          <div class="issued-tip">{{ t('agent_token.claude_config') }}</div>
          <div class="issued-row">
            <code class="mono issued-value">{{ claudeCommand }}</code>
            <el-icon class="hover-icon_with_bg" size="16" @click="copyText(claudeCommand)">
              <icon_copy_outlined></icon_copy_outlined>
            </el-icon>
          </div>
        </div>
      </template>
      <template #footer>
        <template v-if="!issuedToken">
          <el-button secondary @click="closeCreate">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="creating" @click="submitCreate">
            {{ t('agent_token.create') }}
          </el-button>
        </template>
        <el-button v-else type="primary" @click="closeCreate">{{
          t('agent_token.done')
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.sqlbot-agent-token-container {
  background: #ffffff;
  border-radius: 8px;
  row-gap: 24px;
  display: flex;
  flex-direction: column;

  .warn-template {
    display: flex;
    align-items: center;
    background: #d2f1e9;
    border-radius: 6px;
    padding: 9px 16px;

    .icon-span {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      display: flex;
      align-items: center;

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

  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }

  .muted {
    color: #8f959e;
  }

  .token-status {
    display: flex;
    align-items: center;
    font-size: 14px;
    line-height: 22px;

    .ed-icon {
      margin-right: 8px;
    }
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
}

.issued {
  display: flex;
  flex-direction: column;
  row-gap: 8px;

  .issued-tip {
    font-size: 14px;
    color: #646a73;
  }

  .issued-row {
    display: flex;
    align-items: flex-start;
    column-gap: 8px;
    background: #f5f6f7;
    border-radius: 6px;
    padding: 8px 12px;
  }

  .issued-value {
    flex: 1;
    word-break: break-all;
    font-size: 13px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
}
</style>
