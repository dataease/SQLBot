<script lang="ts" setup>
import { ref, shallowRef, computed } from 'vue'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { dsTypeWithImg } from './js/ds-type'

interface Datasource {
  name: string
  type: string
  img: string
  rate?: string
  id?: string
}
withDefaults(
  defineProps<{
    activeName: string
  }>(),
  {
    activeName: '',
  }
)
const keywords = ref('')
const modelList = shallowRef(dsTypeWithImg as Datasource[])
const modelListWithSearch = computed(() => {
  if (!keywords.value) return modelList.value
  return modelList.value.filter((ele) =>
    ele.name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})
const emits = defineEmits(['clickDatasource'])
const handleModelClick = (item: any) => {
  emits('clickDatasource', item)
}
</script>

<template>
  <div class="model-list_side">
    <el-input
      v-model="keywords"
      clearable
      style="width: 232px; margin: 16px 0 8px 24px"
      :placeholder="$t('datasource.search')"
    >
      <template #prefix>
        <el-icon>
          <icon_searchOutline_outlined class="svg-icon" />
        </el-icon>
      </template>
    </el-input>
    <div class="list-content">
      <div
        v-for="ele in modelListWithSearch"
        :key="ele.name"
        class="model"
        :class="activeName === ele.name && 'isActive'"
        @click="handleModelClick(ele)"
      >
        <img width="20px" height="20px" :src="ele.img" />
        <span class="name">{{ ele.name }}</span>
      </div>
      <EmptyBackground
        v-if="!!keywords && !modelListWithSearch.length"
        :description="$t('datasource.relevant_content_found')"
        img-type="tree"
        style="width: 100%; margin-top: 100px"
      />
    </div>
  </div>
</template>

<style lang="less" scoped>
.model-list_side {
  width: 280px;
  height: 100%;
  border-right: 1px solid #1f232926;

  .list-content {
    height: calc(100% - 56px);
    padding: 0 16px;

    .model {
      width: 100%;
      height: 40px;
      display: flex;
      align-items: center;
      padding-left: 8px;
      border-radius: 6px;
      cursor: pointer;
      .name {
        margin-left: 8px;
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
      }
      &:hover {
        background: #1f23291a;
      }

      &.isActive {
        background: var(--ed-color-primary-1a, #1cba901a);
        color: var(--ed-color-primary);
      }
    }
  }
}
</style>
