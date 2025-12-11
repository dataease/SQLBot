<template>
  <div
    v-for="(item, index) in validComponentList"
    :key="item.key"
    class="item"
    :class="{ qrcode: item.key !== 'ldap' }"
    @click="execute(item, index)"
  >
    <el-icon>
      <Icon>
        <component :is="item.icon" class="svg-icon"></component>
      </Icon>
    </el-icon>
    <span class="name">
      {{ item.title }}
    </span>
  </div>
</template>

<script lang="ts" setup>
import { Icon } from '@/components/icon-custom'
import icon_qr_outlined from '@/assets/svg/icon_qr_outlined.svg'
import logo_ldap from '@/assets/svg/logo_ldap.svg'
import icon_pc_outlined from '@/assets/svg/icon_pc_outlined.svg'
import { onMounted, ref } from 'vue'
import { propTypes } from '@/utils/propTypes'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  qrcode: propTypes.bool.def(false),
  ldap: propTypes.bool.def(false),
})

interface OptionItem {
  key: string
  icon: string
  title: string
}

const componentList = ref<OptionItem[]>([
  {
    key: 'qrcode',
    icon: icon_qr_outlined,
    title: t('login.qr_code'),
  },
  {
    key: 'ldap',
    icon: logo_ldap,
    title: 'LDAP',
  },
  {
    key: 'account',
    icon: icon_pc_outlined,
    title: t('user.account'),
  },
])
const componentMap = ref({}) as any
const validComponentList = ref<OptionItem[]>([])

const activeComponent = ref<string>('account')
const initActiveComponent = () => {
  validComponentList.value = []
  componentList.value.forEach((item) => {
    if (item.key !== activeComponent.value && getPropsItem(item.key)) {
      validComponentList.value.push(item)
    }
  })
}
const getPropsItem = (key: string): boolean => {
  if (key === 'qrcode') {
    return props.qrcode
  }
  if (key === 'ldap') {
    return props.ldap
  }
  return false
}
const formatOptionMap = () => {
  componentMap.value['qrcode'] = componentList.value[0]
  componentMap.value['ldap'] = componentList.value[1]
  componentMap.value['account'] = componentList.value[2]
}

const emits = defineEmits(['status-change'])
const execute = (item: OptionItem, index: number) => {
  validComponentList.value[index] = componentMap.value[activeComponent.value]
  activeComponent.value = item.key
  if (activeComponent.value === 'account') {
    showDefaultTabs()
  } else {
    hiddenDefaultTabs()
  }
  emits('status-change', activeComponent.value)
}

const hiddenDefaultTabs = () => {
  const dom = document.getElementsByClassName('default-login-tabs') as any
  const len = dom?.length || 0
  if (len) {
    dom[0]['style']['display'] = 'none'
    if (len > 1) {
      dom[1]['style']['display'] = 'none'
      if (len > 2 && dom[2]) {
        dom[2]['style']['display'] = 'none'
      }
    }
  }
}
const showDefaultTabs = () => {
  const dom = document.getElementsByClassName('default-login-tabs') as any
  const len = dom?.length || 0
  if (len) {
    dom[0]['style']['display'] = ''
    if (len > 1) {
      dom[1]['style']['display'] = ''
      if (len > 2 && dom[2]) {
        dom[2]['style']['display'] = ''
      }
    }
  }
}

const setActive = (active?: string) => {
  const curActive = active || 'account'
  let index = -1
  let item: OptionItem = {
    key: 'account',
    icon: 'icon_pc_outlined',
    title: t('user.account'),
  }
  for (let i = 0; i < validComponentList.value.length; i++) {
    const element = validComponentList.value[i]
    if (element.key === curActive) {
      item = element
      index = i
    }
  }
  validComponentList.value[index] = componentMap.value[activeComponent.value]
  activeComponent.value = item.key
  if (active === 'ldap') {
    hiddenDefaultTabs()
  }
}
defineExpose({
  setActive,
})
onMounted(() => {
  formatOptionMap()
  initActiveComponent()
})
</script>
<style lang="less" scoped>
.item {
  width: 32px;
  cursor: pointer;
  &:hover {
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.15));
  }
  &.qrcode,
  &.account {
    .ed-icon {
      padding: 5px;
      color: #1f2329;
    }
  }

  .ed-icon {
    font-size: 32px;
    border: 1px solid #dee0e3;
    border-radius: 50%;
    color: var(--ed-color-primary);
  }
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: space-between;

  .name {
    margin-top: 8px;
    color: #000;
    text-align: center;
    font-family: var(--ed-color-primary, 'PingFang');
    font-size: 12px;
    font-style: normal;
    font-weight: 400;
    line-height: 20px; /* 166.667% */
    display: none;
  }
}
</style>
