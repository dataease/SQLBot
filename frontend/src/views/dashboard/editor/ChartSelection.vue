<script setup lang="ts">
import { ref } from 'vue'
import SQView from '@/views/dashboard/components/sq-view/index.vue'

const isSelected = ref(false)

const props = defineProps({
  viewInfo: {
    type: Object,
    required: true,
  },
  selectChange: {
    type: Function,
    default: () => {
      return {}
    },
  },
})

const curSelectChange = (value: boolean) => {
  props.selectChange(value)
}
</script>

<template>
  <div class="chart-selection-container">
    <el-checkbox class="select-area" :value="isSelected" @change="curSelectChange"></el-checkbox>
    <SQView :view-info="viewInfo" show-position="multiplexing"></SQView>
  </div>
</template>

<style scoped lang="less">
.chart-selection-container {
  width: 50%;
  height: 320px;
  position: relative;
  padding: 8px;
  float: left;
  overflow: hidden;
  .select-area {
    position: absolute;
    top: 26px;
    right: 20px;
  }
  ::v-deep(.chart-show-area) {
    height: calc(100% - 46px);
  }
}
</style>
