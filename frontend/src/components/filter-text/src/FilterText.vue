<script lang="ts" setup>
import icon_left_outlined from '@/assets/svg/common-back.svg'
import icon_close_outlined from '@/assets/svg/icon_close_outlined.svg'
import icon_deleteTrash_outlined from '@/assets/svg/icon_delete.svg'
import icon_right_outlined from '@/assets/svg/icon_right_outlined.svg'
import { nextTick, ref, watch } from 'vue'
import { Icon } from '@/components/icon-custom'
import { ElButton, ElDivider, ElIcon } from 'element-plus-secondary'
import { propTypes } from '@/utils/propTypes'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const props = defineProps({
  filterTexts: {
    type: Array<string>,
    default: () => [],
  },
  total: propTypes.number.def(0),
})

const emits = defineEmits(['clearFilter'])
const container = ref<any>(null)

const showScroll = ref(false)
const scrollPre = () => {
  container.value!.scrollLeft -= 10
  if (container.value.scrollLeft <= 0) {
    container.value.scrollLeft = 0
  }
}
const scrollNext = () => {
  container.value.scrollLeft += 10
  const width = container.value.scrollWidth - container.value.offsetWidth
  if (container.value.scrollLeft > width) {
    container.value.scrollLeft = width
  }
}
const clearFilter = (index?: number) => {
  emits('clearFilter', index)
}

const clearFilterAll = () => {
  emits('clearFilter', 'empty')
}

watch(
  () => props.filterTexts,
  () => {
    nextTick(() => {
      showScroll.value = container.value?.scrollWidth > container.value?.offsetWidth
    })
  },
  { deep: true }
)
</script>

<template>
  <div v-if="filterTexts.length" class="filter-texts">
    <span class="sum">{{ total }}</span>
    <span class="title">{{ t('common.result_count') }}</span>
    <el-divider direction="vertical" />
    <el-icon v-if="showScroll" class="arrow-left arrow-filter" @click="scrollPre">
      <Icon name="icon_left_outlined"><icon_left_outlined class="svg-icon" /></Icon>
    </el-icon>
    <div ref="container" class="filter-texts-container">
      <p v-for="(ele, index) in filterTexts" :key="ele" class="text">
        <el-tooltip effect="dark" :content="ele" placement="top-start">
          {{ ele }}
        </el-tooltip>
        <el-icon @click="clearFilter(index)">
          <Icon name="icon_close_outlined"><icon_close_outlined class="svg-icon" /></Icon>
        </el-icon>
      </p>
      <el-button
        v-if="!showScroll"
        type="text"
        class="clear-btn clear-btn-inner"
        @click="clearFilterAll"
      >
        <template #icon>
          <Icon name="icon_delete-trash_outlined"
            ><icon_deleteTrash_outlined class="svg-icon"
          /></Icon>
        </template>
        {{ t('common.clear_filter') }}</el-button
      >
    </div>
    <el-icon v-if="showScroll" class="arrow-right arrow-filter" @click="scrollNext">
      <Icon name="icon_right_outlined"><icon_right_outlined class="svg-icon" /></Icon>
    </el-icon>
    <el-button
      v-if="showScroll"
      type="text"
      class="clear-btn"
      style="height: 24px; line-height: 24px"
      @click="clearFilterAll"
    >
      <template #icon>
        <Icon name="icon_delete-trash_outlined"
          ><icon_deleteTrash_outlined class="svg-icon"
        /></Icon>
      </template>
      {{ t('common.clear_filter') }}</el-button
    >
  </div>
</template>

<style lang="less" scoped>
.filter-texts {
  display: flex;
  align-items: center;
  margin: 16px 0;
  font-weight: 400;

  .sum {
    color: #1f2329;
  }

  .title {
    color: #999999;
    margin-left: 8px;
  }

  .text {
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 1px 22px 1px 6px;
    display: inline-block;
    align-items: center;
    color: #0c296e;
    font-size: 14px;
    line-height: 22px;
    background: var(--ed-color-primary-1a, #1cba901a);
    border-radius: 2px;
    margin: 0;
    margin-right: 8px;
    position: relative;

    i {
      position: absolute;
      right: 6px;
      top: 50%;
      font-size: 12px;
      transform: translateY(-50%);
      cursor: pointer;
    }
  }

  .clear-btn {
    color: #646a73;
    padding: 0 4px;
    border-radius: 6px;
    height: 24px;
    line-height: 24px;
  }

  .clear-btn:hover {
    background: #1f23291a;
  }

  .clear-btn:active {
    background: #1f232933;
  }

  .filter-texts-container::-webkit-scrollbar {
    display: none;
  }

  .arrow-filter {
    font-size: 16px;
    width: 24px;
    height: 24px;
    cursor: pointer;
    color: #646a73;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .arrow-filter:hover {
    background: rgba(31, 35, 41, 0.1);
    border-radius: 6px;
  }

  .ed-icon-arrow-right.arrow-filter {
    margin-left: 5px;
  }

  .ed-icon-arrow-left.arrow-filter {
    margin-right: 5px;
  }

  .filter-texts-container {
    flex: 1;
    overflow-x: auto;
    white-space: nowrap;
    height: 24px;

    .clear-btn-inner {
      margin-top: -16px;
    }
  }
}
</style>
