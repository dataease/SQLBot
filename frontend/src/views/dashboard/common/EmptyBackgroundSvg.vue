<script lang="ts" setup>
import nothingSelectDashboard from '@/assets/img/none-dashboard.svg'
defineProps({
  imageSize: {
    type: Number,
    default: 125,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <div class="ed-empty empty-info">
    <div class="ed-empty__image" style="width: 125px">
      <el-icon size="125" class="icon-primary">
        <nothingSelectDashboard></nothingSelectDashboard>
      </el-icon>
    </div>
    <div class="ed-empty__description">
      <p>{{ description }}</p>
    </div>
  </div>
</template>

<style lang="less" scoped>
.empty-info {
  height: 90%;
  padding-top: 0;
}
:deep(.ed-empty__description) {
  margin-top: 8px;
  color: var(--N600, #646a73);
  text-align: center;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
}
</style>
