<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { modelWorkspaceImpact, type ModelImpact, type ModelImpactResolution } from '@/api/workspace'

const { t } = useI18n()
const visible = ref(false)
const impacts = ref<ModelImpact[]>([])
const choices = ref<Record<string, string>>({})
let resolve: ((value: ModelImpactResolution[] | null) => void) | undefined
const incomplete = computed(() =>
  impacts.value.some((item) => item.uses_default && !choices.value[item.workspace_id])
)
const confirm = async (
  modelId: string,
  wsIds?: string[]
): Promise<ModelImpactResolution[] | null> => {
  impacts.value = await modelWorkspaceImpact(modelId, wsIds)
  if (!impacts.value.length) return []
  choices.value = {}
  visible.value = true
  return new Promise((done) => {
    resolve = done
  })
}
const finish = (accepted: boolean) => {
  const value = accepted
    ? impacts.value.map((item) => ({
        workspace_id: item.workspace_id,
        custom_model:
          item.uses_default && choices.value[item.workspace_id] !== 'pause'
            ? choices.value[item.workspace_id]
            : null,
      }))
    : null
  resolve?.(value)
  resolve = undefined
  visible.value = false
}
defineExpose({ confirm })
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="t('workspace_model.impact_title')"
    width="640"
    :close-on-click-modal="false"
    @close="finish(false)"
  >
    <el-alert
      :title="t('workspace_model.impact_hint')"
      type="warning"
      :closable="false"
      show-icon
    />
    <el-form label-position="top" class="model-impact-form">
      <el-form-item v-for="item in impacts" :key="item.workspace_id" :label="item.workspace_name">
        <el-select
          v-if="item.uses_default"
          v-model="choices[item.workspace_id]"
          :placeholder="t('workspace_model.resolve')"
        >
          <el-option :label="t('workspace_model.pause')" value="pause" />
          <el-option
            v-for="model in item.models"
            :key="model.id"
            :label="model.name"
            :value="model.id"
          />
        </el-select>
        <p v-if="item.assistants.length" class="assistant-impact">
          {{ t('workspace_model.assistant_impact', { names: item.assistants.join('、') }) }}
        </p>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button secondary @click="finish(false)">{{ t('common.cancel') }}</el-button>
      <el-button type="danger" :disabled="incomplete" @click="finish(true)">{{
        t('common.confirm2')
      }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped lang="less">
.model-impact-form {
  margin-top: 16px;
  max-height: 420px;
  overflow-y: auto;
  .ed-select {
    width: 100%;
  }
  .assistant-impact {
    margin: 8px 0 0;
    color: #646a73;
  }
}
</style>
