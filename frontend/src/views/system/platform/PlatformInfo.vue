<template>
  <div class="platform-head-container" :class="{ 'just-head': !existInfo }">
    <div class="platform-setting-head">
      <div class="platform-setting-head-left">
        <div class="lead-left-icon">
          <el-icon>
            <Icon name="logo_wechat-work"><component :is="state.cardIcon" class="svg-icon" /></Icon>
          </el-icon>
          <span>{{ cardTitle }}</span>
        </div>
        <div v-if="existInfo" class="lead-left-status" :class="{ invalid: !info.valid }">
          <span>{{
            info.valid ? t('authentication.valid') : info.corpid ? t('authentication.invalid') : ''
          }}</span>
        </div>
      </div>
      <div v-if="existInfo" class="platform-setting-head-right">
        <span>{{ info.enable ? t('platform.status_open') : t('platform.status_close') }}</span>
        <el-switch
          v-if="info.valid"
          v-model="info.enable"
          class="status-switch"
          @change="switchEnableApi"
        />
        <el-tooltip
          v-else
          class="box-item"
          effect="dark"
          :content="t('platform.can_enable_it')"
          placement="top"
        >
          <el-switch
            v-model="info.enable"
            disabled=""
            class="status-switch"
            @change="switchEnableApi"
          />
        </el-tooltip>
      </div>
      <div v-else class="platform-setting-head-right-btn">
        <el-button type="primary" @click="edit">{{ t('platform.access_in') }}</el-button>
      </div>
    </div>
  </div>
  <InfoTemplate
    v-if="existInfo"
    class="platform-setting-main"
    :copy-list="state.copyList"
    :hide-head="true"
    :setting-data="state.settingList"
    @edit="edit"
  />
  <div v-if="existInfo" class="platform-foot-container">
    <el-button type="primary" @click="edit">
      {{ t('datasource.edit') }}
    </el-button>
    <el-button secondary :disabled="!formValid" @click="validate">{{ t('ds.check') }}</el-button>
  </div>
  <platform-form ref="editor" @saved="search" />
</template>

<script lang="ts" setup>
import { ref, type PropType, watch, reactive } from 'vue'
import InfoTemplate from './common/InfoTemplate.vue'
import PlatformForm from './PlatformForm.vue'
import { request } from '@/utils/request'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus-secondary'
import { getPlatformCardConfig, type PlatformCard } from './common/SettingTemplate'
const { t } = useI18n()

const props = defineProps({
  cardInfo: {
    type: Object as PropType<PlatformCard>,
    required: true,
    default: () =>
      ({
        type: 6,
        name: 'wecom',
        config: {},
        enable: false,
        valid: false,
      }) as PlatformCard,
  },
})

const info = ref({}) as any
const state = reactive({
  settingList: [] as any[],
  copyList: [] as string[],
  cardIcon: null,
})

const existInfo = ref(false)
const editor = ref()
const origin = ref(6)

const cardTitle = ref('')
const formValid = ref(false)
watch(
  () => props.cardInfo,
  () => {
    const configData: any = props.cardInfo.config
    configData['id'] = props.cardInfo.id
    configData['enable'] = !!props.cardInfo.enable
    configData['valid'] = !!props.cardInfo.valid
    info.value = configData
    origin.value = props.cardInfo.type

    const platformConfig = getPlatformCardConfig(props.cardInfo.type)
    const list = [...platformConfig.settingList]
    list.forEach((item) => {
      item['pval'] = info.value[item.realKey] || '-'
      // delete item.realKey
    })
    state.settingList = list

    existInfo.value = !!props.cardInfo.id
    cardTitle.value = t(platformConfig.title)

    state.copyList = platformConfig.copyField
    state.cardIcon = platformConfig.icon

    formValid.value = list.every((item: any) => !!info.value[item.realKey])
  },
  { immediate: true }
)
const emits = defineEmits(['saved'])
const search = () => {
  emits('saved')
}

const switchEnableApi = (enable: any) => {
  const url = '/system/authentication/enable'
  const data = { id: origin.value, enable }
  request.patch(url, data).catch(() => {
    info.value.enable = false
  })
}
const edit = () => {
  const data = { ...{ type: origin.value, title: cardTitle.value }, ...info.value }
  editor?.value.edit(data)
}
const validate = () => {
  if (info.value?.agent_id && info.value?.corpsecret) {
    validateHandler()
  }
}
const validateHandler = () => {
  request
    .patch('/system/authentication/status', { type: origin.value, name: '', config: '' })
    .then((res) => {
      if (res) {
        info.value.valid = true
        ElMessage.success(t('ds.connection_success'))
      } else {
        ElMessage.error(t('ds.connection_failed'))
        info.value.enable = false
        info.value.valid = false
      }
    })
    .catch(() => {
      info.value.enable = false
      info.value.valid = false
    })
}
// search()
</script>

<style lang="less" scoped>
.platform-head-container {
  height: 41px;
  border-bottom: 1px solid #1f232926;
}
.just-head {
  height: auto !important;
  border: none !important;
}
.platform-setting-head {
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .platform-setting-head-left {
    display: flex;
    .lead-left-icon {
      display: flex;
      line-height: 24px;
      align-items: center;
      i {
        width: 24px;
        height: 24px;
        font-size: 20px;
      }
      span {
        margin-left: 4px;
        font-family: var(--de-custom_font, 'PingFang');
        font-size: 16px;
        font-style: normal;
        font-weight: 500;
        line-height: 24px;
      }
    }
    .lead-left-status {
      margin-left: 4px;
      height: 24px;
      background: #34c72433;
      padding: 0 6px;
      font-size: 14px;
      border-radius: 2px;
      overflow: hidden;
      span {
        line-height: 24px;
        color: #2ca91f;
      }
    }
    .invalid {
      background: #f54a4533 !important;
      span {
        color: #d03f3b !important;
      }
    }
  }
  .platform-setting-head-right-btn {
    height: 32px;
    line-height: 32px;
  }
  .platform-setting-head-right {
    height: 22px;
    line-height: 24px;
    display: flex;
    span {
      margin-right: 8px;
      font-size: 14px;
      height: 22px;
      line-height: 22px;
    }
    .status-switch {
      line-height: 22px !important;
      height: 22px !important;
    }
  }
}

.platform-setting-main {
  display: inline-block;
  width: 100%;
  padding: 16px 0 0 0 !important;
  ::v-deep(.info-template-content) {
    display: contents !important;
  }
}
.platform-foot-container {
  height: 32px;
  margin-top: -7px;
}
</style>
