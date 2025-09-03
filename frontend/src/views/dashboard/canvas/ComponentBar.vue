<script setup lang="ts">
import { toRefs } from 'vue'
import icon_delete from '@/assets/svg/icon_delete.svg'
import { Icon } from '@/components/icon-custom'
import { useEmitt } from '@/utils/useEmitt.ts'
import { useI18n } from 'vue-i18n'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_chart_preview from '@/assets/svg/icon_chart_preview.svg'
const { t } = useI18n()
const emits = defineEmits(['enlargeView'])

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  configItem: {
    type: Object,
    required: true,
  },
  showPosition: {
    required: false,
    type: String,
    default: 'preview',
  },
  canvasId: {
    type: String,
    default: 'canvas-main',
  },
})

const { configItem } = toRefs(props)

const doPreview = () => {
  // do preview
  emits('enlargeView')
}

const doDeleteComponent = (e: MouseEvent) => {
  e.stopPropagation()
  e.preventDefault()
  useEmitt().emitter.emit(`editor-delete-${props.canvasId}`, configItem.value.id)
}
</script>

<template>
  <div class="component-bar-main" :class="{ 'bar-hidden': !active }">
    <div>
      <el-dropdown
        ref="curDropdown"
        popper-class="bar-main_popper"
        trigger="click"
        placement="bottom-end"
      >
        <el-icon class="bar-more" @mousedown.stop>
          <el-tooltip :content="t('dashboard.more')" placement="bottom">
            <icon name="icon_more_outlined"><icon_more_outlined class="svg-icon" /></icon>
          </el-tooltip>
        </el-icon>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-if="configItem.component === 'SQView'"
              :icon="icon_chart_preview"
              @click="doPreview"
              >{{ t('dashboard.preview') }}</el-dropdown-item
            >
            <el-dropdown-item
              :divided="configItem.component === 'SQView'"
              :icon="icon_delete"
              @click="doDeleteComponent"
              >{{ t('dashboard.delete') }}</el-dropdown-item
            >
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style scoped lang="less">
.component-bar-main {
  height: 20px;
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  z-index: 11;
  cursor: pointer !important;
}

.bar-hidden {
  display: none;
}

.bar-more {
  width: 24px;
  height: 24px;
  color: rgba(31, 35, 41, 1);
  border-radius: 6px;
  background: rgba(255, 255, 255, 1);
  border: 1px solid rgba(217, 220, 223, 1);
  padding: 8px;
  z-index: 10;
  &:hover {
    background-color: rgba(245, 246, 247, 1);
  }

  &:active {
    background-color: rgba(245, 246, 247, 0.5);
  }
}
</style>

<style lang="less">
.bar-main_popper {
  box-shadow: 0px 4px 8px 0px #1f23291a !important;
  border-radius: 4px;
  border: 1px solid #dee0e3 !important;
  width: 120px !important;
  min-width: 120px !important;
  padding: 0 !important;

  .handle-icon {
    color: #646a73;
    margin-right: 8px;
  }

  .ed-dropdown-menu__item--divided {
    margin: 4px 0;
  }

  .ed-dropdown-menu__item {
    position: relative;
    padding-left: 12px;
    background: none;
    color: #1f2329;

    &:focus {
      background: none;
      color: #1f2329;
    }
    &:hover {
      background: none;
      color: #1f2329;
      &::after {
        content: '';
        width: 112px;
        height: 32px;
        border-radius: 4px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1f23291a;
      }
    }
  }
}
</style>
