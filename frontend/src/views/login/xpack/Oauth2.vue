<template>
  <div class="item CAS" @click="execute">
    <el-icon>
      <Icon name="logo_oauth"><logo_oauth class="svg-icon" /></Icon>
    </el-icon>
    <span class="name"> OAuth2 </span>
  </div>
</template>

<script lang="ts" setup>
import logo_oauth from '@/assets/svg/logo_oauth.svg'
import { Icon } from '@/components/icon-custom'
const emits = defineEmits(['switch-category'])
const execute = () => {
  emits('switch-category', { category: 'oauth2', proxy: '/#' })
}
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
