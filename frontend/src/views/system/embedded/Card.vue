<script lang="ts" setup>
import delIcon from '@/assets/svg/icon_delete.svg'
import icon_copy_outlined from '@/assets/embedded/icon_copy_outlined.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_embedded_outlined from '@/assets/embedded/icon_embedded_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import Lock from '@/assets/embedded/LOGO-sql.png'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import LOGO from '@/assets/svg/logo-custom_small.svg'
import { ref, unref, computed } from 'vue'
import { useClipboard } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { ClickOutside as vClickOutside } from 'element-plus-secondary'
import icon_style_set_outlined from '@/assets/svg/icon_style-set_outlined.svg'

const props = withDefaults(
  defineProps<{
    name: string
    isBase: boolean
    description: string
    id?: string
    logo?: string
  }>(),
  {
    name: '-',
    isBase: false,
    id: '-',
    description: '-',
    logo: '',
  }
)
const { copy } = useClipboard({ legacy: true })
const { t } = useI18n()
const emits = defineEmits(['edit', 'del', 'embedded', 'ui'])
const appearanceStore = useAppearanceStoreWithOut()

const handleEdit = () => {
  emits('edit')
}

const handleUi = () => {
  emits('ui')
}

const handleDel = () => {
  emits('del')
}

const handleEmbedded = () => {
  emits('embedded')
}
const copyCode = () => {
  copy(props.id)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
const buttonRef = ref()
const popoverRef = ref()
const onClickOutside = () => {
  unref(popoverRef).popperRef?.delayHide?.()
}
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/assistant/picture/'
const pageLogo = computed(() => {
  return props.logo.startsWith('blob') ? props.logo : baseUrl + props.logo
})
</script>

<template>
  <div class="card">
    <div class="name-icon">
      <img v-if="props.logo" :src="pageLogo" width="32px" height="32px" />
      <el-icon v-else-if="appearanceStore.themeColor === 'custom'" size="32">
        <LOGO></LOGO>
      </el-icon>
      <img v-else :src="Lock" width="32px" height="32px" />
      <div class="id-name">
        <span class="name ellipsis" :title="name">{{ name }}</span>
        <div class="id-copy">
          <span class="id ellipsis" :title="id">{{ id }}</span>
          <el-tooltip :offset="12" effect="dark" :content="t('datasource.copy')" placement="top">
            <el-icon style="cursor: pointer" size="16" @click="copyCode">
              <icon_copy_outlined></icon_copy_outlined>
            </el-icon>
          </el-tooltip>
        </div>
      </div>
      <span class="default" :class="isBase && 'is-base'">{{
        isBase ? $t('embedded.basic_application') : $t('embedded.advanced_application')
      }}</span>
    </div>
    <div class="description" :title="description">{{ description }}</div>
    <div class="methods">
      <el-button secondary @click="handleEmbedded">
        <el-icon style="margin-right: 4px" size="16">
          <icon_embedded_outlined></icon_embedded_outlined>
        </el-icon>
        {{ $t('embedded.embed_third_party') }}
      </el-button>
      <el-button secondary @click="handleEdit">
        <el-icon style="margin-right: 4px" size="16">
          <IconOpeEdit></IconOpeEdit>
        </el-icon>
        {{ $t('dashboard.edit') }}
      </el-button>
      <el-icon ref="buttonRef" v-click-outside="onClickOutside" class="more" size="16" @click.stop>
        <icon_more_outlined></icon_more_outlined>
      </el-icon>

      <el-popover
        ref="popoverRef"
        :virtual-ref="buttonRef"
        virtual-triggering
        trigger="click"
        :teleported="false"
        popper-class="popover-card_embedded"
        placement="bottom-start"
      >
        <div class="content">
          <div class="item" @click.stop="handleUi">
            <el-icon size="16">
              <icon_style_set_outlined></icon_style_set_outlined>
            </el-icon>
            {{ $t('embedded.display_settings') }}
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
  height: 180px;
  border: 1px solid #dee0e3;
  padding: 16px;
  border-radius: 12px;
  &:hover {
    box-shadow: 0px 6px 24px 0px #1f232914;
    .methods {
      display: flex;
    }
  }

  .name-icon {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    .id-name {
      margin-left: 12px;
      max-width: calc(100% - 115px);
      display: flex;
      flex-direction: column;

      .id-copy {
        display: flex;
        align-items: center;
        .id {
          font-weight: 400;
          font-size: 12px;
          line-height: 20px;
          color: #646a73;
          margin-right: 8px;
        }
      }
    }
    .name {
      font-weight: 500;
      font-size: 16px;
      line-height: 24px;
      max-width: 100%;
    }

    .default {
      margin-left: auto;
      padding: 0 4px;
      border-radius: 4px;
      font-weight: 400;
      font-size: 12px;
      line-height: 20px;
      background: #ff880033;
      color: #d97400;
      margin-top: -18px;

      &.is-base {
        background: var(--ed-color-primary-33, #1cba9033);
        color: var(--ed-color-primary-dark-2);
      }
    }
  }

  .description {
    margin-top: 12px;
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    max-width: 100%;
    display: -webkit-box;
    height: 44px;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    word-break: break-word;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .methods {
    margin-top: 16px;
    display: none;
    align-items: center;
    .more {
      position: relative;
      cursor: pointer;
      margin-left: 12px;
      width: 30px;
      height: 30px;

      svg {
        position: relative;
        z-index: 5;
      }

      &::after {
        content: '';
        background: #fff;
        position: absolute;
        border-radius: 6px;
        width: 30px;
        height: 30px;
        transform: translate(-50%, -50%);
        top: 50%;
        left: 50%;
        border: 1px solid #d9dcdf;
        z-index: 1;
      }

      &:hover {
        &::after {
          background: #f5f6f7;
        }
      }
    }
  }
}
</style>

<style lang="less">
.popover-card_embedded.popover-card_embedded.popover-card_embedded {
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
