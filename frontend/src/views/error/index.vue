<template>
  <div class="page-not-found">
    <Icon name="401"><Four class="svg-icon login-logo-icon" /></Icon>
    <span class="span-403">{{ title || routerTitle || '' }}</span>
  </div>
</template>

<script lang="ts" setup>
import Four from '@/assets/svg/401.svg'
import { Icon } from '@/components/icon-custom'
import { propTypes } from '@/utils/propTypes'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
defineProps({
  title: propTypes.string,
})
const routerTitle = computed(() => route.query?.title || '')
</script>
<style lang="less">
.page-not-found {
  height: 100px;
  width: 100%;
  top: calc(50% - 100px);
  position: absolute;
  text-align: center;
}
.span-403 {
  display: block;
  margin: 0;
  font-size: var(--ed-font-size-base);
  color: var(--ed-text-color-secondary);
}
</style>
