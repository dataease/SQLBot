<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import icon_expand_down_filled from '@/assets/svg/icon_expand-down_filled.svg'
import icon_moments_categories_outlined from '@/assets/svg/icon_moments-categories_outlined.svg'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import { userApi } from '@/api/auth'
import { ElMessage } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { highlightKeyword } from '@/utils/xss'

const userStore = useUserStore()
const { t } = useI18n()
defineProps({
  collapse: { type: [Boolean], required: true },
})

const router = useRouter()
const currentWorkspace = ref({
  id: '',
  name: '',
})
const defaultDatasourceList = ref([] as any[])
const workspaceKeywords = ref('')
const defaultWorkspaceListWithSearch = computed(() => {
  if (!workspaceKeywords.value) return defaultDatasourceList.value
  return defaultDatasourceList.value.filter((ele) =>
    ele.name.toLowerCase().includes(workspaceKeywords.value.toLowerCase())
  )
})
const formatKeywords = (item: string) => {
  // Use XSS-safe highlight function
  return highlightKeyword(item, workspaceKeywords.value, 'isSearch')
}

const emit = defineEmits(['selectWorkspace'])

const handleDefaultWorkspaceChange = (item: any) => {
  if (currentWorkspace.value?.id && item.id.toString() === currentWorkspace.value.id.toString()) {
    return
  }
  currentWorkspace.value = { id: item.id, name: item.name }
  userApi.ws_change(item.id).then(() => {
    ElMessage.success(t('common.switch_success'))
    router.push('/chat/index')
    setTimeout(() => {
      location.reload()
    }, 300)
  })
  emit('selectWorkspace', item)
}

const init_ws_data = async () => {
  defaultDatasourceList.value = await userApi.ws_options()
}

const init_current_ws = () => {
  const oid = userStore.getOid
  currentWorkspace.value = defaultDatasourceList.value.find(
    (item) => item.id.toString() === oid.toString()
  )
}
onMounted(async () => {
  await init_ws_data()
  init_current_ws()
})
</script>

<template>
  <el-popover
    trigger="click"
    popper-class="system-workspace"
    :placement="collapse ? 'right' : 'bottom'"
  >
    <template #reference>
      <button class="workspace" :class="collapse && 'collapse'">
        <el-icon size="18">
          <icon_moments_categories_outlined></icon_moments_categories_outlined>
        </el-icon>
        <span v-if="!collapse" :title="currentWorkspace?.name || ''" class="name ellipsis">{{
          currentWorkspace?.name || ''
        }}</span>
        <el-icon v-if="!collapse" style="transform: scale(0.5)" class="expand" size="24">
          <icon_expand_down_filled></icon_expand_down_filled>
        </el-icon></button
    ></template>
    <div class="popover">
      <el-input
        v-model="workspaceKeywords"
        clearable
        style="width: 100%; margin-right: 12px"
        :placeholder="$t('datasource.search_by_name')"
      >
        <template #prefix>
          <el-icon>
            <icon_searchOutline_outlined class="svg-icon" />
          </el-icon>
        </template>
      </el-input>
      <div class="popover-content">
        <el-scrollbar max-height="400px">
          <div
            v-for="ele in defaultWorkspaceListWithSearch"
            :key="ele.name"
            class="popover-item"
            :class="currentWorkspace?.id === ele.id && 'isActive'"
            @click="handleDefaultWorkspaceChange(ele)"
          >
            <el-icon size="16">
              <icon_moments_categories_outlined></icon_moments_categories_outlined>
            </el-icon>
            <div
              :title="ele.name"
              class="datasource-name ellipsis"
              v-html="formatKeywords(ele.name)"
            ></div>
            <el-icon size="16" class="done">
              <icon_done_outlined></icon_done_outlined>
            </el-icon>
          </div>
        </el-scrollbar>

        <div v-if="!defaultWorkspaceListWithSearch.length" class="popover-item empty">
          {{ $t('model.relevant_results_found') }}
        </div>
      </div>
    </div>
  </el-popover>
</template>

<style lang="less" scoped>
.workspace {
  background: #1f23290a;
  border-radius: 6px;
  border: 1px solid #1f23291a;
  padding: 0 12px;
  display: flex;
  align-items: center;
  cursor: pointer;
  width: 208px;
  height: 40px;
  margin-bottom: 12px;

  &.collapse {
    width: 40px;
    background: none;
    border: none;
  }

  .name {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    margin-left: 8px;
    max-width: 120px;
  }

  .expand {
    margin-left: auto;
  }

  &:hover {
    background: #1f23291a;
  }

  &:active {
    background: #1f232926;
  }
}
</style>

<style lang="less">
.system-workspace.system-workspace {
  --ed-popover-border-radius: 6px;
  padding: 4px 0;
  width: 280px !important;
  box-shadow: 0 4px 8px 0 #1f23291a;
  border: 1px solid #dee0e3;
  .ed-input {
    .ed-input__wrapper {
      box-shadow: none;
    }

    border-bottom: 1px solid #1f232926;
  }

  .popover {
    .popover-content {
      padding: 4px;
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      margin-bottom: 2px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      &:not(.empty):hover {
        background: #1f23291a;
      }

      &.empty {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #8f959e;
        cursor: default;
      }

      .datasource-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        max-width: 180px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      .isSearch {
        color: var(--ed-color-primary);
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}
</style>
