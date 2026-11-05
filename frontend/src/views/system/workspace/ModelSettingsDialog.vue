<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus-secondary'
import {
  workspaceModelSettings,
  workspaceModelSettingsUpdate,
  type WorkspaceModelOption,
  type WorkspaceModelSettings,
} from '@/api/workspace'

const { t } = useI18n()
const visible = ref(false)
const busy = ref(false)
const workspaceId = ref('')
const workspaceName = ref('')
const models = ref<WorkspaceModelOption[]>([])
const form = reactive<WorkspaceModelSettings>({ enable_custom_model: false, custom_model: null })
const invalidModel = computed(
  () => !!form.custom_model && !models.value.some((item) => item.id === form.custom_model)
)
const open = async (workspace: { id: string | number; name: string }) => {
  workspaceId.value = String(workspace.id)
  workspaceName.value = workspace.name
  models.value = []
  form.enable_custom_model = false
  form.custom_model = null
  visible.value = true
  busy.value = true
  try {
    const result = await workspaceModelSettings(workspaceId.value)
    models.value = result.models
    form.enable_custom_model = result.enable_custom_model
    form.custom_model = result.custom_model
  } catch {
    visible.value = false
  } finally {
    busy.value = false
  }
}
const save = async () => {
  busy.value = true
  try {
    await workspaceModelSettingsUpdate(workspaceId.value, {
      enable_custom_model: form.enable_custom_model,
      custom_model: form.enable_custom_model ? form.custom_model || null : null,
    })
    ElMessage.success(t('common.save_success'))
    visible.value = false
  } finally {
    busy.value = false
  }
}
defineExpose({ open })
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="t('workspace_model.title')"
    width="600"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    :show-close="!busy"
  >
    <el-form v-loading="busy" label-position="top" class="workspace-model-settings">
      <el-form-item :label="t('user.workspace')">
        <span>{{ workspaceName }}</span>
      </el-form-item>
      <el-form-item :label="t('embedded.useModel')">
        <el-radio-group v-model="form.enable_custom_model">
          <el-radio :value="false">{{ t('workspace_model.system') }}</el-radio>
          <el-radio :value="true">{{ t('workspace_model.custom') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <template v-if="form.enable_custom_model">
        <el-form-item :label="t('workspace_model.default')">
          <el-select
            v-model="form.custom_model"
            clearable
            filterable
            :placeholder="t('workspace_model.select')"
          >
            <el-option
              v-if="invalidModel"
              :value="form.custom_model!"
              :label="t('workspace_model.invalid')"
              disabled
            />
            <el-option
              v-for="model in models"
              :key="model.id"
              :value="model.id"
              :label="model.name"
            />
          </el-select>
        </el-form-item>
        <el-alert
          :title="t(invalidModel ? 'workspace_model.invalid' : 'workspace_model.empty_hint')"
          type="warning"
          :closable="false"
          show-icon
        />
      </template>
      <el-alert v-else :title="t('workspace_model.system_hint')" type="info" :closable="false" />
    </el-form>
    <template #footer>
      <el-button secondary :disabled="busy" @click="visible = false">{{
        t('common.cancel')
      }}</el-button>
      <el-button
        type="primary"
        :loading="busy"
        :disabled="busy || (form.enable_custom_model && invalidModel)"
        @click="save"
        >{{ t('common.save') }}</el-button
      >
    </template>
  </el-dialog>
</template>

<style scoped lang="less">
.workspace-model-settings .ed-select {
  width: 100%;
}
</style>
