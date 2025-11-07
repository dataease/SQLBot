<script lang="ts" setup>
import delIcon from '@/assets/svg/icon_delete.svg'
import icon_admin_outlined from '@/assets/svg/icon_admin_outlined.svg'
import edit from '@/assets/svg/icon_edit_outlined.svg'
import { get_supplier } from '@/entity/supplier'
import { computed, ref } from 'vue'
const props = withDefaults(
  defineProps<{
    name: string
    modelType: string
    baseModel: string
    id?: string
    isDefault?: boolean
    supplier?: number
  }>(),
  {
    name: '-',
    modelType: '-',
    baseModel: '-',
    id: '-',
    isDefault: false,
    supplier: 0,
  }
)
const errorMsg = ref('')
const current_supplier = computed(() => {
  if (!props.supplier) {
    return null
  }
  return get_supplier(props.supplier)
})
const showErrorMask = (msg?: string) => {
  if (!msg) {
    return
  }
  errorMsg.value = msg
  setTimeout(() => {
    errorMsg.value = ''
  }, 3000)
}
const emits = defineEmits(['edit', 'del', 'default'])

const handleDefault = () => {
  emits('default')
}

const handleDel = () => {
  emits('del', { id: props.id, name: props.name, default_model: props.isDefault })
}

const handleEdit = () => {
  emits('edit')
}

defineExpose({ showErrorMask })
</script>

<template>
  <div
    v-loading="!!errorMsg"
    class="card"
    :element-loading-text="errorMsg"
    element-loading-custom-class="model-card-loading"
  >
    <div class="name-icon">
      <img :src="current_supplier?.icon" width="32px" height="32px" />
      <span :title="name" class="name ellipsis">{{ name }}</span>
      <span v-if="isDefault" class="default">{{ $t('model.default_model') }}</span>
    </div>
    <div class="type-value">
      <span class="type">{{ $t('model.model_type') }}</span>
      <span class="value"> {{ modelType.startsWith('modelType.') ? $t(modelType) : modelType }}</span>
    </div>
    <div class="type-value">
      <span class="type">{{ $t('model.basic_model') }}</span>
      <span class="value"> {{ baseModel }}</span>
    </div>
    <div class="methods">
      <el-tooltip
        v-if="isDefault"
        effect="dark"
        :content="$t('common.the_default_model')"
        placement="top"
      >
        <el-button secondary disabled>
          <el-icon style="margin-right: 4px" size="16">
            <icon_admin_outlined></icon_admin_outlined>
          </el-icon>
          {{ $t('common.as_default_model') }}
        </el-button>
      </el-tooltip>

      <el-button v-else secondary @click="handleDefault">
        <el-icon style="margin-right: 4px" size="16">
          <icon_admin_outlined></icon_admin_outlined>
        </el-icon>
        {{ $t('common.as_default_model') }}
      </el-button>
      <el-button secondary @click="handleEdit">
        <el-icon style="margin-right: 4px" size="16">
          <edit></edit>
        </el-icon>
        {{ $t('dashboard.edit') }}
      </el-button>
      <el-button secondary @click="handleDel">
        <el-icon style="margin-right: 4px" size="16">
          <delIcon></delIcon>
        </el-icon>
        {{ $t('dashboard.delete') }}
      </el-button>
    </div>
  </div>
</template>

<style lang="less" scoped>
.card {
  width: 100%;
  height: 176px;
  border: 1px solid #dee0e3;
  padding: 16px;
  border-radius: 12px;
  &:hover {
    box-shadow: 0px 6px 24px 0px #1f232914;
  }

  .name-icon {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    .name {
      margin-left: 12px;
      font-weight: 500;
      font-size: 16px;
      line-height: 24px;
      max-width: calc(100% - 115px);
    }
    .default {
      margin-left: auto;
      background: var(--ed-color-primary-33, #1cba9033);
      padding: 0 4px;
      border-radius: 4px;
      color: var(--ed-color-primary-dark-2);
      font-weight: 400;
      font-size: 12px;
      line-height: 20px;
    }
  }

  .type-value {
    margin-top: 8px;
    display: flex;
    align-items: center;
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    .type {
      color: #646a73;
    }

    .value {
      margin-left: 16px;
    }
  }

  .methods {
    margin-top: 16px;
    align-items: center;
    display: none;

    .divide {
      height: 14px;
      width: 1px;
      background-color: #1f232926;
      margin: 0 12px;
    }
  }

  &:hover {
    .methods {
      display: flex;
    }
  }
  :deep(.model-card-loading) {
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: end;
    background-color: rgb(122 122 122 / 87%);
    .ed-loading-spinner {
      top: auto;
      margin: 8px 4px;
      display: flex;
      position: relative;
      justify-content: flex-end;
      align-items: center;
      width: calc(100% - 8px);
    }
    svg {
      display: none;
    }
    p {
      text-align: left;
      color: var(--ed-color-danger);
    }
  }
}
</style>
