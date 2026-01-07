<template>
  <p class="router-title">{{ t('platform.title') }}</p>

  <div class="sys-setting-p">
    <div class="container-sys-platform">
      <wecom-info />
    </div>
    <!-- <div class="container-sys-platform not-first">
      <dingtalk-info />
    </div> -->
    <!-- <div class="container-sys-platform not-first">
      <lark-info />
    </div>
    <div class="container-sys-platform not-first">
      <larksuite-info />
    </div> -->
  </div>
</template>

<script lang="ts" setup>
import WecomInfo from './wecom/WecomInfo.vue'
/* import DingtalkInfo from './dingtalk/DingtalkInfo.vue' */
/* import LarkInfo from './lark/LarkInfo.vue'
import LarksuiteInfo from './larksuite/LarksuiteInfo.vue' */
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>
<style lang="less" scoped>
.router-title {
  color: #1f2329;
  font-feature-settings:
    'clig' off,
    'liga' off;
  font-family: var(--de-custom_font, 'PingFang');
  font-size: 20px;
  font-style: normal;
  font-weight: 500;
  line-height: 28px;
}
.sys-setting-p {
  width: 100%;
  overflow-y: auto;
  height: calc(100vh - 136px);
  box-sizing: border-box;
  margin-top: 16px;
}
.container-sys-platform {
  padding: 24px;
  overflow: hidden;
  //border-radius: 4px;
  background: var(--ContentBG, #ffffff);

  border-radius: 12px;
  border: 1px solid #dee0e3;
}
.not-first {
  margin-top: 16px;
}
</style>
