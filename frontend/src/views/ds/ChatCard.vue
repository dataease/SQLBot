<script lang="ts" setup>
import icon_form_outlined from '@/assets/svg/icon_form_outlined.svg'
import { computed } from 'vue'
import { dsTypeWithImg } from './js/ds-type'

const props = withDefaults(
  defineProps<{
    name: string
    type: string
    typeName: string
    num: string
    isSelected?: boolean
    description?: string
    id?: string
  }>(),
  {
    name: '-',
    type: '-',
    description: '-',
    id: '-',
    typeName: '-',
    isSelected: false,
  }
)

const emits = defineEmits(['selectDs', 'selectDsDirectly'])
const icon = computed(() => {
  return (dsTypeWithImg.find((ele) => props.type === ele.type) || {}).img
})

const SelectDs = () => {
  emits('selectDs')
}

const SelectDsDirectly = () => {
  emits('selectDsDirectly')
}
</script>

<template>
  <div
    class="card"
    :class="isSelected && 'is-selected'"
    @dblclick="SelectDsDirectly"
    @click="SelectDs"
  >
    <div class="name-icon">
      <img :src="icon" width="32px" height="32px" />
      <div class="info">
        <div :title="name" class="name ellipsis">{{ name }}</div>
        <div class="type">{{ typeName }}</div>
      </div>
    </div>
    <div :title="description" class="type-value">
      {{ description }}
    </div>

    <div class="bottom-info">
      <div class="form-rate">
        <el-icon class="form-icon" size="16">
          <icon_form_outlined></icon_form_outlined>
        </el-icon>
        {{ num }}
      </div>
      <div click.stop class="methods"></div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.card {
  width: 100%;
  border: 1px solid #dee0e3;
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;

  &:hover {
    box-shadow: 0px 6px 24px 0px #1f232914;
  }

  .name-icon {
    display: flex;
    align-items: center;
    margin-bottom: 12px;

    .info {
      margin-left: 12px;
      .name {
        font-weight: 500;
        font-size: 16px;
        line-height: 24px;
        max-width: 250px;
      }
      .type {
        font-weight: 400;
        font-size: 12px;
        line-height: 20px;
        color: #646a73;
      }
    }
  }

  .type-value {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    color: #646a73;
    height: 44px;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    word-break: break-word;
    width: 100%;
  }

  .bottom-info {
    margin-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 28px;

    .ed-button {
      height: 28px;
      min-width: 78px;
    }

    .form-rate {
      display: flex;
      align-items: center;
      color: #646a73;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;

      .form-icon {
        margin-right: 8px;
      }
    }

    .methods {
      align-items: center;
      display: none;

      .more {
        position: relative;
        cursor: pointer;

        &::after {
          content: '';
          background-color: #1f23291a;
          position: absolute;
          border-radius: 6px;
          width: 24px;
          height: 24px;
          transform: translate(-50%, -50%);
          top: 50%;
          left: 50%;
          display: none;
        }

        &:hover {
          &::after {
            display: block;
          }
        }
      }
    }
  }

  &.is-selected {
    border: 1px solid var(--ed-color-primary);
    background: var(--ed-color-primary-1a, #1cba901a);
  }
}
</style>
