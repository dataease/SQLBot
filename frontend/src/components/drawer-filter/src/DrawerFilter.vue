<script setup lang="ts">
import { propTypes } from '@/utils/propTypes'
import { ElSelect, ElOption } from 'element-plus-secondary'
import { computed, reactive } from 'vue'
import { useEmitt } from '@/utils/useEmitt'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const props = defineProps({
  optionList: propTypes.arrayOf(
    propTypes.shape({
      id: propTypes.string,
      name: propTypes.string,
    })
  ),
  index: propTypes.number,
  title: propTypes.string,
  single: propTypes.bool,
  property: {
    type: Object,
    default: () => ({}),
  },
})

const state = reactive({
  activeStatus: props.single ? undefined : [],
})
const emits = defineEmits(['filter-change'])

const selectStatus = (ids: any[] | any) => {
  let _list
  if (ids instanceof Array) {
    _list = ids
  } else {
    _list = [ids]
  }
  emits(
    'filter-change',
    _list.map((item) => item.id || item.value)
  )
}

const optionListNotSelect = computed(() => {
  return [...(props.optionList as any[])]
})
const clear = (index: number) => {
  if (index !== props.index) return
  state.activeStatus = props.single ? undefined : []
}

useEmitt({
  name: 'clear-drawer_main',
  callback: clear,
})
</script>

<template>
  <div class="draw-filter_base">
    <span>{{ title }}</span>
    <div class="filter-item">
      <el-select
        v-model="state.activeStatus"
        :teleported="false"
        style="width: 100%"
        value-key="id"
        filterable
        :placeholder="t('datasource.Please_select') + props.property.placeholder"
        :multiple="!props.single"
        @change="selectStatus"
      >
        <el-option
          v-for="item in optionListNotSelect"
          :key="item.name"
          :label="item.name"
          :value="item"
        />
      </el-select>
    </div>
  </div>
</template>
<style lang="less" scope>
.draw-filter_base {
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
  }
}
</style>
