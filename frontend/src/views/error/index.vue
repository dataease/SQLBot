<template>
  <div class="page-not-found">
    <Icon name="401"><Four class="svg-icon login-logo-icon" /></Icon>

    <span v-if="showTimer" class="span-403">{{ unauthorizedTitle }}</span>
    <span v-else class="span-403">{{ title || routerTitle || '' }}</span>
  </div>
</template>

<script lang="ts" setup>
import Four from '@/assets/svg/401.svg'
import { Icon } from '@/components/icon-custom'
import { propTypes } from '@/utils/propTypes'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toLoginPage } from '@/utils/utils'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
defineProps({
  title: propTypes.string,
})
const routerTitle = computed(() => route.query?.title || '')

const target = computed(() => route.query?.target || '')

const showTimer = computed(() => routerTitle.value && routerTitle.value === 'unauthorized')
const target_full_path = ref('')
const unauthorizedTitle = ref(t('login.no_auth_error', [3]))

onMounted(() => {
  if (target.value) {
    target_full_path.value = target.value as string
    if (!target_full_path.value.startsWith('/')) {
      target_full_path.value = '/' + target_full_path.value
    }

    /* setTimeout(() => {
      router.push(toLoginPage(target_full_path))
    }, 2000) */
  }
  if (showTimer.value) {
    let timer = 3
    const timerHandler = setInterval(() => {
      if (timer-- <= 0) {
        clearInterval(timerHandler)
        router.push(toLoginPage(target_full_path.value))
        return
      }
      unauthorizedTitle.value = t('login.no_auth_error', [timer])
    }, 1000)
  }
})
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
