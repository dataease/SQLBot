<script lang="ts" setup>
import { onMounted, ref, computed, shallowRef } from 'vue'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import { chatApi, ChatInfo } from '@/api/chat.ts'
import { datasourceApi } from '@/api/datasource.ts'
import Card from '@/views/ds/ChatCard.vue'
import AddDrawer from '@/views/ds/AddDrawer.vue'
import { useUserStore } from '@/stores/user'
import { useAssistantStore } from '@/stores/assistant'
import { request } from '@/utils/request'
const assistantStore = useAssistantStore()
const userStore = useUserStore()

const isWsAdmin = computed(() => userStore.isAdmin || userStore.isSpaceAdmin)
const selectAssistantDs = computed(
  () => assistantStore.getAssistant && !assistantStore.getEmbedded && !assistantStore.getAutoDs
)
const props = withDefaults(
  defineProps<{
    hidden?: boolean
  }>(),
  {
    hidden: false,
  }
)

const addDrawerRef = ref()
const searchLoading = ref(false)
const datasourceConfigVisible = ref(false)
const keywords = ref('')
const datasourceList = shallowRef([] as any[])
const datasourceListWithSearch = computed(() => {
  if (!keywords.value) return datasourceList.value
  return datasourceList.value.filter((ele) =>
    ele.name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})
const beforeClose = () => {
  datasourceConfigVisible.value = false
  keywords.value = ''
}

const emits = defineEmits(['onChatCreated'])

function listDs() {
  searchLoading.value = true
  ;(selectAssistantDs.value ? request.get('/system/assistant/ds') : datasourceApi.list())
    .then((res) => {
      datasourceList.value = res
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const innerDs = ref()

const loading = ref(false)
const statusLoading = ref(false)

function showDs() {
  listDs()
  datasourceConfigVisible.value = true
}

function hideDs() {
  innerDs.value = undefined
  datasourceConfigVisible.value = false
}

function selectDsInDialog(ds: any) {
  innerDs.value = ds.id
}

function confirmSelectDs() {
  if (innerDs.value) {
    if (assistantStore.getType == 1) {
      createChat(innerDs.value)
      return
    }
    statusLoading.value = true
    //check first
    datasourceApi
      .check_by_id(innerDs.value)
      .then((res: any) => {
        if (res) {
          createChat(innerDs.value)
        }
      })
      .finally(() => {
        statusLoading.value = false
      })
  }
}

function createChat(datasource: number) {
  loading.value = true
  const param = {
    datasource: datasource,
  } as any
  let method = chatApi.startChat
  if (assistantStore.getAssistant) {
    param['origin'] = 2
    method = chatApi.startAssistantChat
  }
  method(param)
    .then((res) => {
      const chat: ChatInfo | undefined = chatApi.toChatInfo(res)
      if (chat == undefined) {
        throw Error('chat is undefined')
      }
      emits('onChatCreated', chat)
      hideDs()
    })
    .catch((e) => {
      console.error(e)
    })
    .finally(() => {
      loading.value = false
    })
}

onMounted(() => {
  if (props.hidden) {
    return
  }
})

const handleAddDatasource = () => {
  addDrawerRef.value.handleAddDatasource()
}

defineExpose({
  showDs,
  hideDs,
  createChat,
})
</script>

<template>
  <div v-loading.body.fullscreen.lock="loading || statusLoading">
    <el-drawer
      v-model="datasourceConfigVisible"
      :close-on-click-modal="false"
      size="calc(100% - 100px)"
      modal-class="datasource-drawer-chat"
      direction="btt"
      :before-close="beforeClose"
      :show-close="false"
    >
      <template #header="{ close }">
        <span style="white-space: nowrap">{{ $t('qa.select_datasource') }}</span>
        <div class="flex-center" style="width: 100%; margin-right: 32px">
          <el-input
            v-model="keywords"
            clearable
            style="width: 320px; max-width: calc(100% - 32px)"
            :placeholder="$t('datasource.search')"
          >
            <template #prefix>
              <el-icon>
                <icon_searchOutline_outlined />
              </el-icon>
            </template>
          </el-input>
        </div>
        <el-icon class="ed-dialog__headerbtn mrt" style="cursor: pointer" @click="close">
          <icon_close_outlined></icon_close_outlined>
        </el-icon>
      </template>
      <div v-if="datasourceListWithSearch.length" class="card-content">
        <el-row :gutter="16" class="w-full">
          <el-col
            v-for="ele in datasourceListWithSearch"
            :key="ele.id"
            :xs="24"
            :sm="12"
            :md="12"
            :lg="8"
            :xl="6"
            class="mb-16"
          >
            <Card
              :id="ele.id"
              :key="ele.id"
              :name="ele.name"
              :type="ele.type"
              :type-name="ele.type_name"
              :num="ele.num"
              :is-selected="ele.id === innerDs"
              :description="ele.description"
              @select-ds="selectDsInDialog(ele)"
            ></Card>
          </el-col>
        </el-row>
      </div>
      <template v-if="!keywords && !datasourceListWithSearch.length && !searchLoading">
        <EmptyBackground
          class="datasource-yet_btn"
          :description="$t('datasource.data_source_yet')"
          img-type="noneWhite"
        />

        <div v-if="isWsAdmin" style="text-align: center; margin-top: -10px">
          <el-button type="primary" @click="handleAddDatasource">
            <template #icon>
              <icon_add_outlined></icon_add_outlined>
            </template>
            {{ $t('datasource.new_data_source') }}
          </el-button>
        </div>
      </template>
      <EmptyBackground
        v-if="!!keywords && !datasourceListWithSearch.length"
        :description="$t('datasource.relevant_content_found')"
        class="datasource-yet"
        img-type="tree"
      />
      <template #footer>
        <div class="dialog-footer">
          <el-button secondary :disabled="loading" @click="hideDs">{{
            $t('common.cancel')
          }}</el-button>
          <el-button
            :type="loading || statusLoading || innerDs === undefined ? 'info' : 'primary'"
            :disabled="loading || statusLoading || innerDs === undefined"
            @click="confirmSelectDs"
          >
            {{ $t('datasource.confirm') }}
          </el-button>
        </div>
      </template>
    </el-drawer>
    <AddDrawer ref="addDrawerRef" @search="listDs"></AddDrawer>
  </div>
</template>

<style lang="less">
.datasource-drawer-chat {
  .ed-drawer__body {
    padding: 16px 0 16px 0;
  }
  .card-content {
    max-height: calc(100% - 40px);
    overflow-y: auto;
    padding: 0 8px 0 24px;

    .w-full {
      width: 100%;
    }

    .mb-16 {
      margin-bottom: 16px;
    }
  }

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
  }

  .datasource-yet_btn {
    height: auto !important;
    padding-top: 200px;
    padding-bottom: 0;
  }
}
</style>
