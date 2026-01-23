<template>
  <el-tabs v-model="activeName" class="qr-tab" @tab-click="handleClick">
    <el-tab-pane v-if="props.wecom" :label="t('user.wecom')" name="wecom"></el-tab-pane>
    <el-tab-pane v-if="props.dingtalk" :label="t('user.dingtalk')" name="dingtalk"></el-tab-pane>
    <el-tab-pane v-if="props.lark" :label="t('user.lark')" name="lark"></el-tab-pane>
    <el-tab-pane v-if="props.larksuite" :label="t('user.larksuite')" name="larksuite"></el-tab-pane>
  </el-tabs>
  <div v-if="activeName === 'wecom'" class="login-qrcode">
    <div class="title">
      <el-icon>
        <Icon name="logo_wechat-work"><logo_wechatWork class="svg-icon" /></Icon>
      </el-icon>
      {{ t('user.wecom') + t('login.scan_qr_login') }}
    </div>
    <div class="qrcode">
      <wecom-qr v-if="activeName === 'wecom'" />
    </div>
  </div>
  <div v-if="activeName === 'dingtalk'" class="login-qrcode">
    <div class="title">
      <el-icon>
        <Icon name="logo_dingtalk"><logo_dingtalk class="svg-icon" /></Icon>
      </el-icon>
      {{ t('user.dingtalk') + t('login.scan_qr_login') }}
    </div>
    <div class="qrcode">
      <dingtalk-qr v-if="activeName === 'dingtalk'" />
    </div>
  </div>
  <div v-if="activeName === 'lark'" class="login-qrcode">
    <div class="title">
      <el-icon>
        <Icon name="logo_lark"><logo_lark class="svg-icon" /></Icon>
      </el-icon>
      {{ t('user.lark') + t('login.scan_qr_login') }}
    </div>
    <div class="qrcode">
      <lark-qr v-if="activeName === 'lark'" />
    </div>
  </div>
  <div v-if="activeName === 'larksuite'" class="login-qrcode">
    <div class="title">
      <el-icon>
        <Icon name="logo_lark"><logo_lark class="svg-icon" /></Icon>
      </el-icon>
      {{ t('user.larksuite') + t('login.scan_qr_login') }}
    </div>
    <div class="qrcode">
      <larksuite-qr v-if="activeName === 'larksuite'" />
    </div>
  </div>
</template>

<script lang="ts" setup>
import logo_wechatWork from '@/assets/svg/logo_wechat-work.svg'
import logo_dingtalk from '@/assets/svg/logo_dingtalk.svg'
import logo_lark from '@/assets/svg/logo_lark.svg'
import { ref } from 'vue'
import LarkQr from './LarkQr.vue'
import LarksuiteQr from './LarksuiteQr.vue'
import DingtalkQr from './DingtalkQr.vue'
import WecomQr from './WecomQr.vue'
import { propTypes } from '@/utils/propTypes'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const activeName = ref('')
const props = defineProps({
  wecom: propTypes.bool.def(false),
  lark: propTypes.bool.def(false),
  dingtalk: propTypes.bool.def(false),
  larksuite: propTypes.bool.def(false),
})
const initActive = () => {
  const qrArray = ['wecom', 'dingtalk', 'lark', 'larksuite'] as const
  for (let i = 0; i < qrArray.length; i++) {
    const key = qrArray[i]
    if (props[key as keyof typeof props]) {
      activeName.value = key
      break
    }
  }
}
const handleClick = () => {}
initActive()
</script>

<style lang="less" scoped>
.login-qrcode {
  margin: 24px 0;
  height: 274px;
  display: flex;
  align-items: center;
  row-gap: 12px;
  flex-direction: column;
  .qrcode {
    max-width: 286px;
    display: flex;
    overflow: hidden;
    justify-content: center;
    align-items: center;
    border-radius: 8px;
    background: #fff;
  }

  .title {
    display: flex;
    align-items: center;
    justify-content: center;
    // margin: 24px 0 12px 0;
    font-family: var(--de-custom_font, 'PingFang');
    font-size: 20px;
    font-style: normal;
    font-weight: 500;
    line-height: 28px;
    column-gap: 8px;
    color: #1f2329;
    height: 28px;
    .ed-icon {
      font-size: 24px;
    }
  }
}
.qr-tab {
  width: auto;
  --ed-tabs-header-height: 34px;
  ::v-deep(.ed-tabs__item) {
    font-size: 14px;
    font-weight: 400;
    align-items: start;
  }
}
</style>
