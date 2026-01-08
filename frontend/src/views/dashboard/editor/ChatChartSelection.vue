<template>
  <el-drawer
    v-model="dialogShow"
    direction="btt"
    size="90%"
    trigger="click"
    :title="t('dashboard.add_chart')"
    modal-class="custom-drawer"
    :destroy-on-close="true"
    @closed="handleClose()"
  >
    <el-container class="chat-container">
      <el-aside class="chat-container-left">
        <el-container class="chat-container-right-container">
          <el-main class="chat-list">
            <DashboardChatList
              v-model:loading="loading"
              :current-chat-id="currentChatId"
              :chat-list="chatList"
              @chat-selected="onClickHistory"
            />
          </el-main>
        </el-container>
      </el-aside>
      <el-container :loading="loading">
        <el-main v-if="!loading" class="chat-record-list">
          <el-scrollbar ref="chatListRef" style="padding: 8px">
            <chart-selection
              v-for="(viewInfo, index) in chartInfoList"
              :key="index"
              :view-info="viewInfo"
              :select-change="(value: boolean) => selectChange(value, viewInfo)"
            >
            </chart-selection>
          </el-scrollbar>
        </el-main>
      </el-container>
    </el-container>

    <template #footer>
      <el-row class="multiplexing-footer">
        <el-col class="adapt-count">
          <span>{{ t('dashboard.chart_selected', [selectComponentCount]) }} </span>
        </el-col>
        <el-button secondary class="close-button" @click="dialogShow = false"
          >{{ t('common.cancel') }}
        </el-button>
        <el-button
          type="primary"
          :disabled="!selectComponentCount"
          class="confirm-button"
          @click="saveMultiplexing"
          >{{ t('common.confirm2') }}
        </el-button>
      </el-row>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Chat, chatApi, ChatInfo } from '@/api/chat.ts'
import DashboardChatList from '@/views/dashboard/editor/DashboardChatList.vue'
import ChartSelection from '@/views/dashboard/editor/ChartSelection.vue'
import { concat } from 'lodash-es'

const dialogShow = ref(false)
const { t } = useI18n()
const selectComponentCount = computed(() => state.curMultiplexingComponents.length)
const state = reactive({
  curMultiplexingComponents: [],
})

const loading = ref<boolean>(false)
const chatList = ref<Array<ChatInfo>>([])

const currentChatId = ref<number | undefined>()
const currentChat = ref<ChatInfo>(new ChatInfo())
const chartInfoList = ref<Array<any>>([])
const emits = defineEmits(['addChatChart'])

function selectChange(value: boolean, viewInfo: any) {
  if (value) {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    state.curMultiplexingComponents.push(viewInfo)
  } else {
    state.curMultiplexingComponents = state.curMultiplexingComponents.filter(
      // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
      (component) => component.id !== viewInfo.id
    )
  }
}

const getData = (record: any) => {
  const recordData = record.data
  if (record?.predict_record_id !== undefined && record?.predict_record_id !== null) {
    let _list = []
    if (record?.predict_data && typeof record?.predict_data === 'string') {
      if (
        record?.predict_data.length > 0 &&
        record?.predict_data.trim().startsWith('[') &&
        record?.predict_data.trim().endsWith(']')
      ) {
        try {
          _list = JSON.parse(record?.predict_data)
        } catch (e) {
          console.error(e)
        }
      }
    } else {
      if (record?.predict_data.length > 0) {
        _list = record?.predict_data
      }
    }

    if (_list.length == 0) {
      return _list
    }

    if (recordData.data && recordData.data.length > 0) {
      recordData.data = concat(recordData.data, _list)
    } else {
      recordData.data = _list
    }

    return recordData
  } else {
    return recordData
  }
}

function adaptorChartInfoList(chatInfo: ChatInfo) {
  chartInfoList.value = []
  if (chatInfo && chatInfo.records) {
    chatInfo.records.forEach((record: any) => {
      const data = getData(record)
      if (
        ((record?.analysis_record_id === undefined || record?.analysis_record_id === null) &&
          (record?.predict_record_id === undefined || record?.predict_record_id === null) &&
          (record?.sql || record?.chart)) ||
        (record?.predict_record_id !== undefined &&
          record?.predict_record_id !== null &&
          data?.data?.length > 0)
      ) {
        const recordeInfo = { id: chatInfo.id + '_' + record.id, data: data, chart: {} }
        const chartBaseInfo = JSON.parse(record.chart)
        if (chartBaseInfo) {
          let yAxis = []
          const axis = chartBaseInfo?.axis
          if (!axis?.y) {
            yAxis = []
          } else {
            const y = axis.y
            const multiQuotaValues = axis['multi-quota']?.value || []

            // 统一处理为数组
            const yArray = Array.isArray(y) ? [...y] : [{ ...y }]

            // 标记 multi-quota
            yAxis = yArray.map((item) => ({
              ...item,
              'multi-quota': multiQuotaValues.includes(item.value),
            }))
          }

          recordeInfo['chart'] = {
            type: chartBaseInfo?.type,
            title: chartBaseInfo?.title,
            columns: chartBaseInfo?.columns,
            xAxis: axis?.x ? [axis?.x] : [],
            yAxis: yAxis,
            series: axis?.series ? [axis?.series] : [],
            multiQuotaName: axis?.['multi-quota']?.name,
          }
          chartInfoList.value.push(recordeInfo)
        }
      }
    })
  }
}

function onClickHistory(chat: Chat) {
  currentChat.value = new ChatInfo(chat)
  if (chat !== undefined && chat.id !== undefined && !loading.value) {
    currentChatId.value = chat.id
    loading.value = true
    chatApi
      .get_with_Data(chat.id)
      .then((res) => {
        const info = chatApi.toChatInfo(res)
        if (info) {
          currentChat.value = info
          adaptorChartInfoList(info)
          state.curMultiplexingComponents = []
        }
      })
      .finally(() => {
        loading.value = false
      })
  }
}

function getChatList() {
  loading.value = true
  chatApi
    .list()
    .then((res) => {
      chatList.value = chatApi.toChatInfoList(res)
    })
    .finally(() => {
      loading.value = false
    })
}

const dialogInit = () => {
  dialogShow.value = true
  currentChatId.value = undefined
  state.curMultiplexingComponents = []
  chartInfoList.value = []
  getChatList()
}

const saveMultiplexing = () => {
  dialogShow.value = false
  if (state.curMultiplexingComponents.length > 0) {
    emits('addChatChart', state.curMultiplexingComponents)
  }
}
const handleClose = () => {}
defineExpose({
  dialogInit,
})
</script>

<style lang="less" scoped>
.close-button {
  position: absolute;
  top: 18px;
  right: 120px;
}

.confirm-button {
  position: absolute;
  top: 18px;
  right: 20px;
}

.multiplexing-area {
  width: 100%;
  height: 100%;
}

.multiplexing-footer {
  position: relative;
}

.adapt-count {
  position: absolute;
  top: 18px;
  left: 20px;
  color: #646a73;
  font-size: 14px;
  font-weight: 400;
  line-height: 22px;
}

.adapt-select {
  position: absolute;
  top: 18px;
  right: 220px;
}

.adapt-text {
  font-size: 14px;
  font-weight: 400;
  color: #1f2329;
  line-height: 22px;
}

.chat-container {
  height: 100%;
  .chat-container-left {
    padding-top: 20px;
    --ed-aside-width: 260px;
    border-radius: 12px 0 0 12px;
    border-right: 1px solid rgba(31, 35, 41, 0.15);
    .chat-container-right-container {
      height: 100%;

      .chat-list-header {
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .chat-list {
        padding: 0 0 20px 0;
      }
    }
  }

  .chat-record-list {
    padding: 0 0 20px 0;
  }

  .chat-footer {
    --ed-footer-height: 120px;

    display: flex;
    flex-direction: column;

    .input-wrapper {
      flex: 1;

      position: relative;

      .input-area {
        height: 100%;
        padding-bottom: 8px;

        :deep(.ed-textarea__inner) {
          height: 100% !important;
        }
      }

      .input-icon {
        min-width: unset;
        position: absolute;
        bottom: 14px;
        right: 8px;
      }
    }
  }

  .send-btn {
    min-width: 0;
  }
}
</style>

<style lang="less">
.custom-drawer {
  .ed-drawer__footer {
    height: 64px !important;
    padding: 0 !important;
    box-shadow: 0 -1px 0px #d7d7d7 !important;
  }

  .ed-drawer__body {
    background: rgba(245, 246, 247, 1) !important;
    padding: 0 0 64px 0 !important;
  }
}
</style>
