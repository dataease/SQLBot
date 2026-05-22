<script lang="ts" setup>
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import type { Placement } from 'element-plus-secondary'

export interface Menu {
  svgName?: string
  label?: string
  command: string
  divided?: boolean
  disabled?: boolean
}

withDefaults(
  defineProps<{
    menuList: Menu[]
    placement?: Placement
    // eslint-disable-next-line vue/require-default-prop
    iconName?: any
    iconSize?: string
    inTable?: boolean
  }>(),
  {
    placement: 'bottom-end',
    iconSize: '16px',
    inTable: false,
  }
)

const handleCommand = (command: string | number | object) => {
  emit('handleCommand', command)
}

const emit = defineEmits(['handleCommand'])
</script>

<template>
  <el-dropdown
    popper-class="menu-more_popper"
    :placement="placement"
    :persistent="false"
    trigger="click"
    @command="handleCommand"
  >
    <el-icon class="hover-icon" :class="inTable && 'hover-icon-in-table'" @click.stop>
      <component :is="iconName || icon_more_outlined" class="svg-icon"></component>
    </el-icon>
    <template #dropdown>
      <el-dropdown-menu :persistent="false">
        <template v-for="ele in menuList" :key="ele">
          <el-dropdown-item :divided="ele.divided" :command="ele.command" :disabled="ele.disabled">
            <el-icon v-if="ele.svgName" class="handle-icon" :style="{ fontSize: iconSize }">
              <component :is="ele.svgName"></component>
            </el-icon>
            {{ ele.label }}
          </el-dropdown-item>
        </template>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="less">
.menu-more_popper {
  box-shadow: 0px 4px 8px 0px #1f23291a !important;
  border-radius: 6px;
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
        border-radius: 6px;
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
