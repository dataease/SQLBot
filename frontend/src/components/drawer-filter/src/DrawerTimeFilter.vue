<script setup lang="ts">
import { propTypes } from '@/utils/propTypes'
import { computed, reactive, toRefs } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmitt } from '@/utils/useEmitt.ts'
const { t } = useI18n()

const props = defineProps({
  property: {
    type: Object,
    default: () => ({}),
  },
  index: propTypes.number,
  title: propTypes.string,
})
const { property } = toRefs(props)
const timeConfig = computed(() => {
  let obj = Object.assign(
    {
      showType: 'datetime',
      rangeSeparator: '-',
      startPlaceholder: t('common.start_time'),
      endPlaceholder: t('common.end_time'),
      format: 'YYYY-MM-DD HH:mm:ss',
      valueFormat: 'YYYY-MM-DD HH:mm:ss',
      size: 'default',
      placement: 'bottom-end',
    },
    property.value
  )
  return obj
})
const state = reactive({
  modelValue: [],
})

const emits = defineEmits(['filter-change'])
const onChange = () => {
  emits('filter-change', state.modelValue)
}
const clear = (index: number) => {
  if (index !== props.index) return
  state.modelValue = []
}

useEmitt({
  name: 'clear-drawer_main',
  callback: clear,
})

defineExpose({
  clear,
})
</script>

<template>
  <div class="draw-filter_time">
    <span>{{ title }}</span>
    <div class="filter-item">
      <el-date-picker
        key="drawer-time-filt"
        v-model="state.modelValue"
        :type="timeConfig.showType"
        :range-separator="timeConfig.rangeSeparator"
        :start-placeholder="timeConfig.startPlaceholder"
        :end-placeholder="timeConfig.endPlaceholder"
        :format="timeConfig.format"
        :value-format="timeConfig.valueFormat"
        :size="timeConfig.size"
        :placement="timeConfig.placement"
        @change="onChange"
      />
    </div>
  </div>
</template>
<style lang="less" scope>
.draw-filter_time {
  margin-bottom: 16px;

  > :nth-child(1) {
    color: var(--deTextSecondary, #1f2329);
    font-style: normal;
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    white-space: nowrap;
  }

  .filter-item {
    margin-top: 8px;
    .ed-date-editor {
      width: 100%;
    }
  }
}
</style>
