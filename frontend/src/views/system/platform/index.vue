<template>
  <p class="router-title">{{ t('platform.title') }}</p>

  <div class="sys-setting-p">
    <div v-for="card in state.cardList" :key="card.type" class="container-sys-platform">
      <platform-info :card-info="card" @saved="loadData" />
    </div>
  </div>
</template>

<script lang="ts" setup>
import PlatformInfo from './PlatformInfo.vue'

import { useI18n } from 'vue-i18n'
import { request } from '@/utils/request'
import { onMounted, reactive } from 'vue'
import type { PlatformCard } from './common/SettingTemplate'
const { t } = useI18n()

const state = reactive({
  cardList: [] as PlatformCard[],
})

const loadData = () => {
  const url = '/system/platform'
  request.get(url).then((res: any) => {
    state.cardList = res
      .map((item: any) => {
        item.config = JSON.parse(item.config)
        return item
      })
      .filter((card: any) => card.type < 8)
  })
}
onMounted(() => {
  loadData()
})
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
  row-gap: 16px;
  display: flex;
  flex-direction: column;
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
