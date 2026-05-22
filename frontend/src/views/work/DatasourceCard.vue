<script lang="ts" setup>
import { Document } from '@element-plus/icons-vue'
withDefaults(
  defineProps<{
    name: string
    description: string
    creator: string
  }>(),
  {
    name: '',
    description: '',
    creator: '',
  }
)
</script>

<template>
  <div class="datasource-card">
    <div class="description">
      <el-icon size="20" style="margin-right: 12px">
        <Document></Document>
      </el-icon>
      <span class="value">{{ name }}</span>
    </div>
    <div class="description">
      <span class="key">describe:</span>
      <span class="value">{{ description }}</span>
    </div>
    <div class="description">
      <span class="key">Founder:</span>
      <span class="value">{{ creator }}</span>
    </div>
  </div>
</template>

<style lang="less" scoped>
.datasource-card {
  height: 120px;
  padding: 16px;
  border-radius: 6px;
  box-shadow: 0px 0px 12px rgba(0, 0, 0, 0.12);
  .description {
    display: flex;
    align-items: center;
    width: 100%;
    margin-bottom: 8px;
    .key {
      margin-right: 12px;
    }
  }
}
</style>
