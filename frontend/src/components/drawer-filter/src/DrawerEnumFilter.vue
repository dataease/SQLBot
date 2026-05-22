<script setup lang="ts">
import { propTypes } from '@/utils/propTypes'
import { reactive } from 'vue'
import { useEmitt } from '@/utils/useEmitt'

const props = defineProps({
  optionList: propTypes.arrayOf(
    propTypes.shape({
      id: propTypes.string,
      name: propTypes.string,
    })
  ),
  index: propTypes.number,
  title: propTypes.string,
})

const state = reactive<{ activeStatus: any[]; optionList: any[] }>({
  activeStatus: [],
  optionList: [],
})

const nodeChange = (id: string | number) => {
  const len = state.activeStatus.indexOf(id)
  if (len >= 0) {
    state.activeStatus.splice(len, 1)
  } else {
    state.activeStatus.push(id)
  }
  emits('filter-change', state.activeStatus)
}

const emits = defineEmits(['filter-change'])
const clear = (index: number) => {
  if (index !== props.index) return
  state.activeStatus = []
}

useEmitt({
  name: 'clear-drawer_main',
  callback: clear,
})
</script>

<template>
  <div class="draw-filter_enum">
    <span>{{ title }}</span>
    <div class="filter-item">
      <span
        v-for="ele in props.optionList"
        :key="ele.id"
        class="item"
        :class="[state.activeStatus.includes(ele.id) ? 'active' : '']"
        @click="nodeChange(ele.id)"
        >{{ ele.name }}</span
      >
    </div>
  </div>
</template>
<style lang="less" scope>
.draw-filter_enum {
  margin-bottom: 4px;

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
    .item,
    .more {
      font-family: var(--de-custom_font, 'PingFang');
      white-space: nowrap;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      margin-right: 12px;
      text-align: center;
      padding: 1px 6px;
      background: var(--deTextPrimary5, #f5f6f7);
      color: var(--deTextPrimary, #1f2329);
      border-radius: 6px;
      cursor: pointer;
      display: inline-block;
      margin-bottom: 12px;
    }

    .active,
    .more:hover {
      background: var(--ed-color-primary-1a, #1cba901a);
      color: #0b4a3a;
    }

    .more {
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
      i {
        margin-right: 5px;
      }
    }
  }
}
</style>
<style lang="less">
.filter-popper {
  padding: 0 !important;
  background: #fff !important;
}
</style>
