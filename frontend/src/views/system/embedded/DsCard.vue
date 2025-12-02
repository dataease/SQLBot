<script lang="ts" setup>
import icon_form_outlined from '@/assets/svg/icon_form_outlined.svg'
import icon_personal_privacy_outlined from '@/assets/embedded/icon_personal-privacy_outlined.svg'
import icon_community_tab_outlined from '@/assets/embedded/icon_community-tab_outlined.svg'
import { computed } from 'vue'
import { dsTypeWithImg } from '@/views/ds/js/ds-type'

const props = withDefaults(
  defineProps<{
    name: string
    type: string
    typeName: string
    num: string
    description?: string
    isPrivate: boolean
  }>(),
  {
    name: '-',
    type: '-',
    description: '-',
    isPrivate: false,
    typeName: '-',
    num: '-',
  }
)

const emits = defineEmits(['active', 'private', 'public'])
const icon = computed(() => {
  return (dsTypeWithImg.find((ele) => props.type === ele.type) || {}).img
})
const handleActive = () => {
  emits('active')
}

const handlePrivate = () => {
  emits('private')
}

const handlePublic = () => {
  emits('public')
}
</script>

<template>
  <div class="card" @click="handleActive">
    <div class="name-icon">
      <img :src="icon" width="32px" height="32px" />
      <div class="info">
        <div class="name ellipsis" :title="name">{{ name }}</div>
        <div class="type">{{ typeName }}</div>
      </div>
      <span class="default" :class="isPrivate && 'is-private'">{{
        isPrivate ? $t('embedded.private') : $t('embedded.public')
      }}</span>
    </div>
    <div class="type-value">
      {{ description }}
    </div>

    <div class="bottom-info">
      <div class="form-rate">
        <el-icon class="form-icon" size="16">
          <icon_form_outlined></icon_form_outlined>
        </el-icon>
        {{ num }}
      </div>
      <div click.stop class="methods">
        <el-button v-if="isPrivate" secondary @click.stop="handlePublic">
          <el-icon style="margin-right: 4px" size="16">
            <icon_community_tab_outlined></icon_community_tab_outlined>
          </el-icon>
          {{ $t('embedded.set_to_public') }}
        </el-button>
        <el-button v-else secondary @click.stop="handlePrivate">
          <el-icon style="margin-right: 4px" size="16">
            <icon_personal_privacy_outlined></icon_personal_privacy_outlined>
          </el-icon>
          {{ $t('embedded.set_to_private') }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.card {
  width: 370px;
  border: 1px solid #dee0e3;
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;
  margin: 16px 16px 0 0;
  &:hover {
    box-shadow: 0px 6px 24px 0px #1f232914;
  }

  .name-icon {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    position: relative;

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

    .default {
      background: var(--ed-color-primary-33, #1cba9033);
      padding: 0 4px;
      border-radius: 4px;
      color: var(--ed-color-primary-dark-2);
      font-weight: 400;
      font-size: 12px;
      line-height: 20px;
      position: absolute;
      right: 0;
      top: 12px;

      &.is-private {
        background: #f54a4533;
        color: #d03f3b;
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
    word-break: break-word;
    overflow: hidden;
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
  &:hover {
    .methods {
      display: flex;
    }
  }
}
</style>

<style lang="less">
.popover-card_ds_copy.popover-card_ds_copy.popover-card_ds_copy {
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border-radius: 4px;
  border: 1px solid #dee0e3;
  width: fit-content !important;
  min-width: 120px !important;
  padding: 0;
  .content {
    position: relative;
    &::after {
      position: absolute;
      content: '';
      top: 40px;
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
        border-radius: 4px;
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
