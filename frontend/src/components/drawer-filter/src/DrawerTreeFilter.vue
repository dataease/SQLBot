<script setup lang="ts">
import { propTypes } from '@/utils/propTypes'
import { ElTreeSelect } from 'element-plus-secondary'
import { computed, reactive, ref, toRefs, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmitt } from '@/utils/useEmitt.ts'
const { t } = useI18n()
const props = defineProps({
  optionList: propTypes.arrayOf(
    propTypes.shape({
      value: propTypes.string,
      label: propTypes.string,
      children: Array,
      disabled: Boolean,
    })
  ),
  index: propTypes.number,
  title: propTypes.string,
  property: {
    type: Object,
    default: () => ({}),
  },
})

const { property } = toRefs(props)
const treeConfig = computed(() => {
  let obj = Object.assign(
    {
      checkStrictly: false,
      showCheckbox: true,
      checkOnClickNode: true,
      placeholder: t('user.role'),
    },
    property.value
  )
  return obj
})

const state = reactive({
  currentStatus: [],
  activeStatus: [],
})

const emits = defineEmits(['filter-change'])
const filterTree = ref()
const treeChange = () => {
  const nodes = state.currentStatus.map((id) => {
    return filterTree.value?.getNode(id).data
  })
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.activeStatus = [...nodes]
  emits(
    'filter-change',
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    state.activeStatus.map((item) => item.value)
  )
}
const optionListNotSelect = computed(() => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  return [...props.optionList]
})

const clear = (index: number) => {
  if (index !== props.index) return
  state.currentStatus = []
}

useEmitt({
  name: 'clear-drawer_main',
  callback: clear,
})

watch(
  () => state.currentStatus,
  () => {
    treeChange()
  },
  {
    immediate: true,
  }
)
defineExpose({
  clear,
})
</script>

<template>
  <div class="draw-filter_tree">
    <span>{{ title }}</span>
    <div class="filter-item">
      <el-tree-select
        ref="filterTree"
        v-model="state.currentStatus"
        node-key="value"
        :teleported="false"
        style="width: 100%"
        :data="optionListNotSelect"
        :highlight-current="true"
        multiple
        :render-after-expand="false"
        :placeholder="t('datasource.Please_select') + treeConfig.placeholder"
        :show-checkbox="treeConfig.showCheckbox"
        :check-strictly="treeConfig.checkStrictly"
        :check-on-click-node="treeConfig.checkOnClickNode"
      />
    </div>
  </div>
</template>
<style lang="less" scope>
.draw-filter_tree {
  margin-bottom: 16px;

  > :nth-child(1) {
    color: var(--deTextSecondary, #1f2329);
    font-family: var(--de-custom_font, 'PingFang');
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
