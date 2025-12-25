<script lang="ts" setup>
import { ref, reactive, computed } from 'vue'
import { ElDrawer, ElButton } from 'element-plus-secondary'
import { propTypes } from '@/utils/propTypes'
import DrawerFilter from '@/components/drawer-filter/src/DrawerFilter.vue'
import DrawerEnumFilter from '@/components/drawer-filter/src/DrawerEnumFilter.vue'
import { useEmitt } from '@/utils/useEmitt'
import { useI18n } from 'vue-i18n'
import DrawerTreeFilter from '@/components/drawer-filter/src/DrawerTreeFilter.vue'
import DrawerTimeFilter from '@/components/drawer-filter/src/DrawerTimeFilter.vue'
const { t } = useI18n()
const props = defineProps({
  filterOptions: propTypes.arrayOf(
    propTypes.shape({
      type: propTypes.string,
      field: propTypes.string,
      option: propTypes.array,
      title: propTypes.string,
      property: propTypes.shape({}),
    })
  ),
  title: propTypes.string,
})

const componentList = computed(() => {
  return props.filterOptions as any[]
})

const state = reactive<{ conditions: any[] }>({
  conditions: [],
})
const userDrawer = ref(false)

const init = () => {
  userDrawer.value = true
}

const clear = (index: any) => {
  useEmitt().emitter.emit('clear-drawer_main', index)
}
const cleanrInnerValue = (index: number) => {
  const field = componentList.value[index]?.field
  if (!field) {
    return
  }
  clear(index)
  for (let i = 0; i < state.conditions.length; i++) {
    if (state.conditions[i].field === field) {
      state.conditions[i].value = []
    }
  }
}
const clearInnerTag = (index?: number) => {
  if (isNaN(index as number)) {
    for (let i = 0; i < componentList.value.length; i++) {
      clear(i)
    }
    return
  }
  const condition = state.conditions[index as number]
  const field = condition?.field
  for (let i = 0; i < componentList.value.length; i++) {
    if (componentList.value[i].field === field) {
      clear(i)
    }
  }
}
const clearFilter = (id?: number) => {
  clearInnerTag(id)
  if (isNaN(id as number)) {
    const len = state.conditions.length
    state.conditions.splice(0, len)
  } else {
    state.conditions.splice(id as number, 1)
  }
  trigger()
}
const filterChange = (value: any, field: any, operator: any) => {
  let exits = false
  let len = state.conditions.length
  while (len--) {
    const condition = state.conditions[len]
    if (condition.field === field) {
      exits = true
      condition['value'] = value
    }
    if (!condition?.value?.length) {
      state.conditions.splice(len, 1)
    }
  }
  if (!exits && value?.length) {
    state.conditions.push({ field, value, operator })
  }
  treeFilterChange(value, field, operator)
}
const reset = () => {
  clearFilter()
  userDrawer.value = false
}
const close = () => {
  userDrawer.value = false
}
const emits = defineEmits(['trigger-filter', 'tree-filter-change'])
const trigger = () => {
  emits('trigger-filter', state.conditions)
}
const treeFilterChange = (value: any, field: any, operator: any) => {
  emits('tree-filter-change', {
    value,
    field,
    operator,
  })
}
defineExpose({
  init,
  clearFilter,
  close,
  cleanrInnerValue,
})
</script>

<template>
  <el-drawer
    v-model="userDrawer"
    :title="t('user.filter_conditions')"
    size="600px"
    modal-class="drawer-main-container"
    direction="rtl"
  >
    <div v-for="(component, index) in componentList" :key="index">
      <drawer-tree-filter
        v-if="component.type === 'tree-select'"
        :option-list="component.option"
        :title="component.title"
        :property="component.property"
        :index="index"
        @filter-change="(v) => filterChange(v, component.field, 'in')"
      />
      <drawer-filter
        v-if="component.type === 'select'"
        :option-list="component.option"
        :title="component.title"
        :index="index"
        :property="component.property"
        @filter-change="(v) => filterChange(v, component.field, 'in')"
      />
      <drawer-enum-filter
        v-if="component.type === 'enum'"
        :option-list="component.option"
        :title="component.title"
        :index="index"
        @filter-change="(v) => filterChange(v, component.field, 'in')"
      />
      <drawer-time-filter
        v-if="component.type === 'time'"
        :title="component.title"
        :property="component.property"
        :index="index"
        @filter-change="(v) => filterChange(v, component.field, component.operator)"
      />
    </div>

    <template #footer>
      <el-button secondary @click="reset">{{ t('common.reset') }}</el-button>
      <el-button type="primary" @click="trigger">{{ t('common.search') }}</el-button>
    </template>
  </el-drawer>
</template>

<style lang="less">
.drawer-main-container {
  .ed-drawer__body {
    padding: 16px 24px 80px !important;
  }
  .ed-drawer__footer {
    padding: 16px 24px;
    height: 64px;
  }
}
</style>
