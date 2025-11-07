<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { supplierList } from '@/entity/supplier'

const { t } = useI18n()
const keywords = ref('')

const modelListWithSearch = computed(() => {
  if (!keywords.value) return supplierList
  return supplierList.filter((ele) => {
    if (!ele.i18nKey) {
      return ele.name.toLowerCase().includes(keywords.value.toLowerCase())
    }
    const translatedName = t(ele.i18nKey).toLowerCase()
    const originalName = ele.name.toLowerCase()
    const searchTerm = keywords.value.toLowerCase()
    return translatedName.includes(searchTerm) || originalName.includes(searchTerm)
  })
})
const emits = defineEmits(['clickModel'])
const handleModelClick = (item: any) => {
  emits('clickModel', item)
}
</script>

<template>
  <div class="model-list">
    <div class="title">{{ $t('model.select_supplier') }}</div>
    <el-input
      v-model="keywords"
      clearable
      style="width: 100%; margin-right: 12px"
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
        @click="handleModelClick(ele)"
      >
        <img width="32px" height="32px" :src="ele.icon" />
        <span class="name">{{ ele.i18nKey ? $t(ele.i18nKey) : ele.name }}</span>
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
.model-list {
  width: 800px;
  margin: 0 auto;
  max-height: 100%;
  padding-top: 24px;
  .title {
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
    margin-bottom: 16px;
  }

  .list-content {
    margin-top: 16px;
    display: flex;
    height: calc(100% - 40px);
    flex-wrap: wrap;
    .model:nth-child(odd) {
      margin-left: 0;
    }

    .model {
      width: 392px;
      height: 64px;
      display: flex;
      align-items: center;
      padding-left: 16px;
      margin-bottom: 16px;
      border: 1px solid #dee0e3;
      border-radius: 12px;
      margin-left: 16px;
      cursor: pointer;
      &:hover {
        box-shadow: 0px 6px 24px 0px #1f232914;
      }
      .name {
        margin-left: 12px;
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
      }
    }
  }
}
</style>
