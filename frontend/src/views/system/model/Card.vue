<script lang="ts" setup>
import delIcon from '@/assets/svg/icon_delete.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_moments_categories_outlined from '@/assets/svg/icon_moments-categories_outlined.svg'
import icon_admin_outlined from '@/assets/svg/icon_admin_outlined.svg'
import icon_describe_outlined from '@/assets/svg/icon_describe_outlined.svg'
import edit from '@/assets/svg/icon_edit_outlined.svg'
import { get_supplier } from '@/entity/supplier'
import { computed, ref, unref } from 'vue'
const props = withDefaults(
  defineProps<{
    name: string
    modelType: string
    baseModel: string
    id?: string
    isDefault?: boolean
    supplier?: number
    num?: number
  }>(),
  {
    name: '-',
    modelType: '-',
    baseModel: '-',
    id: '-',
    isDefault: false,
    supplier: 0,
    num: 0,
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
const emits = defineEmits(['edit', 'del', 'default', 'authorizedSpace', 'editworkspaceList'])

const handleDefault = () => {
  emits('default')
}

const handleDel = () => {
  emits('del', { id: props.id, name: props.name, default_model: props.isDefault })
}

const handleEdit = () => {
  emits('edit')
}

const handleEditWorkspaceList = () => {
  emits('editworkspaceList')
}
const handleAuthorizedSpace = () => {
  emits('authorizedSpace')
}
const buttonRef = ref()
const popoverRef = ref()
const onClickOutside = () => {
  unref(popoverRef).popperRef?.delayHide?.()
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
      <span class="value">
        {{ modelType.startsWith('modelType.') ? $t(modelType) : modelType }}</span
      >
    </div>
    <div class="type-value">
      <span class="type">{{ $t('model.basic_model') }}</span>
      <span class="value"> {{ baseModel }}</span>
    </div>
    <div class="type-value">
      <span class="type">{{ $t('authorized_space.authorized_space') }}</span>
      <span class="value" style="display: flex; align-items: center">
        {{ $t('permission.2', { msg: num }) }}
        <el-tooltip
          v-if="false"
          effect="dark"
          :content="$t('authorized_space.authorized_space_list')"
          placement="top"
          offset="12"
        >
          <el-icon
            class="hover-icon_with_bg"
            style="cursor: pointer; margin-left: 8px"
            size="16"
            @click="handleEditWorkspaceList"
          >
            <icon_describe_outlined></icon_describe_outlined>
          </el-icon>
        </el-tooltip>
      </span>
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

      <el-icon
        ref="buttonRef"
        v-click-outside="onClickOutside"
        class="more"
        size="16"
        style="color: #646a73"
        @click.stop
      >
        <icon_more_outlined></icon_more_outlined>
      </el-icon>
      <el-popover
        ref="popoverRef"
        :virtual-ref="buttonRef"
        virtual-triggering
        trigger="click"
        :teleported="false"
        popper-class="popover-card_workspace"
        placement="bottom-start"
      >
        <div class="content">
          <div class="item" @click.stop="handleAuthorizedSpace">
            <el-icon size="16">
              <icon_moments_categories_outlined></icon_moments_categories_outlined>
            </el-icon>
            {{ $t('authorized_space.authorized_space') }}
          </div>
          <div class="item" @click.stop="handleDel">
            <el-icon size="16">
              <delIcon></delIcon>
            </el-icon>
            {{ $t('dashboard.delete') }}
          </div>
        </div>
      </el-popover>
    </div>
  </div>
</template>

<style lang="less" scoped>
.card {
  width: 100%;
  height: 206px;
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
      border-radius: 6px;
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
    display: flex;

    .divide {
      height: 14px;
      width: 1px;
      background-color: #1f232926;
      margin: 0 12px;
    }
    .more {
      position: relative;
      cursor: pointer;
      margin-left: 12px;
      width: 32px;
      height: 32px;

      svg {
        position: relative;
        z-index: 10;
      }

      &::after {
        content: '';
        position: absolute;
        border-radius: 6px;
        width: 30px;
        height: 30px;
        transform: translate(-50%, -50%);
        top: 50%;
        left: 50%;
        background: #fff;
        border: 1px solid #d9dcdf;
      }

      &:hover {
        &::after {
          background-color: #f5f6f7;
        }
      }
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

<style lang="less">
.popover-card_workspace.popover-card_workspace.popover-card_workspace {
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border-radius: 6px;
  border: 1px solid #dee0e3;
  width: fit-content !important;
  min-width: 120px !important;
  padding: 0;

  .content {
    position: relative;

    &::after {
      position: absolute;
      content: '';
      top: 39px !important;
      left: 0;
      width: 100%;
      height: 1px;
      background: #dee0e3;
    }

    .item {
      position: relative;
      padding: 0 12px;
      height: 40px;
      display: flex;
      align-items: center;
      cursor: pointer;

      .ed-icon {
        margin-right: 8px;
        color: #646a73;
      }

      &:hover {
        &::after {
          display: block;
        }
      }

      &::after {
        content: '';
        width: calc(100% - 8px);
        height: 32px;
        border-radius: 6px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1f23291a;
        display: none;
      }
    }
  }
}
</style>
