<template>
  <div class="info-template-container">
    <div v-if="!props.hideHead" class="info-template-header">
      <div class="info-template-title">
        <span>{{ curTitle }}</span>
      </div>
      <div>
        <el-button v-if="testConnectText" secondary @click="check">{{ testConnectText }}</el-button>
        <el-button v-if="showValidate" secondary @click="check">{{
          t('datasource.validate')
        }}</el-button>
        <el-button type="primary" @click="edit">{{ t('commons.edit') }}</el-button>
      </div>
    </div>
    <div class="info-template-content clearfix">
      <div v-for="item in settingList" :key="item.pkey" class="info-content-item">
        <div class="info-item-label">
          <!-- <span>{{ t(item.pkey) }}</span> -->
          <span>{{ item.pkey }}</span>
          <el-tooltip
            v-if="tooltipItem[item.pkey]"
            effect="dark"
            :content="tooltipItem[item.pkey]"
            placement="top"
          >
            <el-icon class="info-tips"
              ><Icon name="dv-info"><dvInfo class="svg-icon" /></Icon
            ></el-icon>
          </el-tooltip>
        </div>
        <div class="info-item-content">
          <div v-if="item.type === 'pwd'" class="info-item-pwd">
            <span class="info-item-pwd-span">{{
              pwdItem[item.pkey]['hidden'] ? '********' : item.pval
            }}</span>

            <el-tooltip
              v-if="props.copyList.includes(item.pkey)"
              effect="dark"
              :content="t('datasource.copy')"
              placement="top"
            >
              <el-button text class="setting-tip-btn" @click="copyVal(item.pval)">
                <template #icon>
                  <Icon name="de-copy"><icon_copy_outlined class="svg-icon" /></Icon>
                </template>
              </el-button>
            </el-tooltip>

            <el-tooltip
              effect="dark"
              :content="
                pwdItem[item.pkey]['hidden']
                  ? t('embedded.click_to_show')
                  : t('embedded.click_to_hide')
              "
              placement="top"
            >
              <el-button text class="setting-tip-btn" @click="switchPwd(item.pkey)">
                <template #icon>
                  <Icon
                    ><component
                      :is="
                        pwdItem[item.pkey]['hidden']
                          ? icon_invisible_outlined
                          : icon_visible_outlined
                      "
                      class="svg-icon"
                    ></component
                  ></Icon>
                </template>
              </el-button>
            </el-tooltip>
          </div>
          <!-- <span v-else-if="item.pkey.includes('basic.dsIntervalTime')">
            <span>{{ item.pval + ' ' + executeTime + t('common.every_exec') }}</span>
          </span> -->
          <template v-else>
            <div class="info-item-content-val">
              <span style="word-break: break-all">{{ item.pval }}</span>
              <el-tooltip
                v-if="props.copyList.includes(item.pkey)"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon class="info-tips hover-icon_with_bg" @click="copyVal(item.pval)">
                  <icon_copy_outlined class="svg-icon" />
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import icon_invisible_outlined from '@/assets/embedded/icon_invisible_outlined.svg'
import icon_visible_outlined from '@/assets/embedded/icon_visible_outlined.svg'
import dvInfo from '@/assets/svg/dashboard-info.svg'
import { ref, computed, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClipboard } from '@vueuse/core'
import { ElMessage } from 'element-plus-secondary'
import type { SettingRecord, ToolTipRecord } from './SettingTemplate'
const { copy } = useClipboard({ legacy: true })
const { t } = useI18n()
const props = defineProps({
  settingKey: {
    type: String,
    default: 'basic',
  },
  labelTooltips: {
    type: Array as PropType<ToolTipRecord[]>,
    default: () => [],
  },
  settingData: {
    type: Array as PropType<SettingRecord[]>,
    default: () => [],
  },
  settingTitle: {
    type: String,
    default: '',
  },
  hideHead: {
    type: Boolean,
    default: false,
  },
  showValidate: {
    type: Boolean,
    default: false,
  },
  testConnectText: {
    type: String,
    default: null,
  },
  copyList: {
    type: Array as PropType<string[]>,
    default: () => [],
  },
})
// const executeTime = ref(t('system.and_0_seconds'))
const curTitle = computed(() => {
  return props.settingTitle || t('system.basic_settings')
})
const copyVal = async (val: any) => {
  try {
    await copy(val)
    ElMessage.success(t('embedded.copy_successful'))
  } catch (e) {
    console.error(e)
    ElMessage.warning(t('embedded.copy_failed'))
  }
}
const loadList = () => {
  settingList.value = []
  if (props.settingData?.length) {
    props.settingData.forEach((item) => {
      /* if (item.pkey.includes('basic.dsExecuteTime')) {
        executeTime.value = getExecuteTime(item.pval)
      } else {
        settingList.value.push(item)
      } */
      settingList.value.push(item)
    })
  }
}

/* const getExecuteTime = (val: any) => {
  const options = [
    { value: 'minute', label: t('system.time_0_seconds') },
    { value: 'hour', label: t('system.and_0_seconds_de') },
  ]
  return options.filter((item) => item.value === val)[0].label
} */

const settingList = ref([] as SettingRecord[])

const init = () => {
  if (props.settingData?.length) {
    loadList()
  }
}
const pwdItem = ref({} as Record<string, { hidden: boolean }>)

const formatPwd = () => {
  settingList.value.forEach((setting) => {
    if (setting.type === 'pwd') {
      pwdItem.value[setting.pkey] = { hidden: true }
    }
  })
}

const tooltipItem = ref({} as Record<string, any>)
const formatLabel = () => {
  if (props.labelTooltips?.length) {
    props.labelTooltips.forEach((tooltip) => {
      tooltipItem.value[tooltip.key] = tooltip.val
    })
  }
}

const switchPwd = (pkey: string) => {
  pwdItem.value[pkey]['hidden'] = !pwdItem.value[pkey]['hidden']
}

const emits = defineEmits(['edit', 'check'])
const edit = () => {
  emits('edit')
}

const check = () => {
  emits('check')
}
defineExpose({
  init,
})
init()
formatPwd()
formatLabel()
</script>

<style lang="less" scope>
.setting-tip-btn {
  height: 24px !important;
  width: 24px !important;
  margin-left: 4px !important;
  .ed-icon {
    font-size: 16px;
  }
}
.info-template-container {
  padding: 24px 24px 8px 24px;
  background: var(--ContentBG, #ffffff);
  border-radius: 4px;
  .info-template-header {
    display: flex;
    margin-top: -4px;
    align-items: center;
    justify-content: space-between;
    .info-template-title {
      height: 24px;
      line-height: 23px;
      font-size: 16px;
      font-weight: 500;
      color: #1f2329;
    }
  }
  .info-template-content {
    width: 100%;
    margin-top: 12px;
    .info-content-item {
      width: 50%;
      float: left;
      margin-bottom: 16px;
      min-height: 46px;
      .info-item-label {
        height: 22px;
        line-height: 22px;
        display: flex;
        align-items: center;
        span {
          font-size: 14px;
          color: #646a73;
          font-weight: 400;
        }
        i {
          margin-left: 2px;
        }
      }
      .info-item-content {
        line-height: 22px;
        span {
          font-size: 14px;
          color: #1f2329;
          font-weight: 400;
        }

        .info-item-pwd {
          height: 22px;
          line-height: 22px;
          width: 100%;
          display: flex;
          align-items: center;
          i {
            margin-left: 2px;
          }
          .info-item-pwd-span {
            max-width: calc(100% - 84px);
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
          }
        }
        .info-item-content-val {
          display: flex;
          align-items: center;
          column-gap: 6px;
          .hover-icon_with_bg {
            color: var(--ed-color-primary);
            background-color: var(--ed-button-hover-bg-color);
            /* &::after {
              background: var(--ed-button-hover-bg-color);
            } */
          }
        }
      }
    }
  }
  .clearfix::after {
    content: '';
    display: table;
    clear: both;
  }
}
</style>
