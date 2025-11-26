<script setup lang="ts">
import BaseAnswer from './BaseAnswer.vue'
import { chatApi, ChatInfo, type ChatMessage, ChatRecord } from '@/api/chat.ts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import MdComponent from '@/views/chat/component/MdComponent.vue'
import ChartBlock from '@/views/chat/chat-block/ChartBlock.vue'

const props = withDefaults(
  defineProps<{
    recordId?: number
    chatList?: Array<ChatInfo>
    currentChatId?: number
    currentChat?: ChatInfo
    message?: ChatMessage
    loading?: boolean
  }>(),
  {
    recordId: undefined,
    chatList: () => [],
    currentChatId: undefined,
    currentChat: () => new ChatInfo(),
    message: undefined,
    loading: false,
  }
)

const emits = defineEmits([
  'finish',
  'error',
  'scrollBottom',
  'stop',
  'update:loading',
  'update:chatList',
  'update:currentChat',
  'update:currentChatId',
])

const index = computed(() => {
  if (props.message?.index) {
    return props.message.index
  }
  if (props.message?.index === 0) {
    return 0
  }
  return -1
})

const _currentChatId = computed({
  get() {
    return props.currentChatId
  },
  set(v) {
    emits('update:currentChatId', v)
  },
})

const _currentChat = computed({
  get() {
    return props.currentChat
  },
  set(v) {
    emits('update:currentChat', v)
  },
})

const _chatList = computed({
  get() {
    return props.chatList
  },
  set(v) {
    emits('update:chatList', v)
  },
})

const _loading = computed({
  get() {
    return props.loading
  },
  set(v) {
    emits('update:loading', v)
  },
})

const stopFlag = ref(false)
const sendMessage = async () => {
  stopFlag.value = false
  _loading.value = true

  if (index.value < 0) {
    _loading.value = false
    return
  }

  const currentRecord: ChatRecord = _currentChat.value.records[index.value]

  let error: boolean = false
  if (_currentChatId.value === undefined || currentRecord.predict_record_id === undefined) {
    error = true
  }
  if (error) return

  try {
    const controller: AbortController = new AbortController()
    const response = await chatApi.predict(currentRecord.predict_record_id, controller)
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    let predict_answer = ''
    let predict_content = ''

    let tempResult = ''

    while (true) {
      if (stopFlag.value) {
        controller.abort()
        _loading.value = false
        break
      }

      const { done, value } = await reader.read()
      if (done) {
        _loading.value = false
        break
      }

      let chunk = decoder.decode(value, { stream: true })
      tempResult += chunk
      const split = tempResult.match(/data:.*}\n\n/g)
      if (split) {
        chunk = split.join('')
        tempResult = tempResult.replace(chunk, '')
      } else {
        continue
      }
      if (chunk && chunk.startsWith('data:{')) {
        if (split) {
          for (const str of split) {
            let data
            try {
              data = JSON.parse(str.replace('data:{', '{'))
            } catch (err) {
              console.error('JSON string:', str)
              throw err
            }

            if (data.code && data.code !== 200) {
              ElMessage({
                message: data.msg,
                type: 'error',
                showClose: true,
              })
              return
            }

            switch (data.type) {
              case 'id':
                currentRecord.id = data.id
                _currentChat.value.records[index.value].id = data.id
                break
              case 'info':
                console.info(data.msg)
                break
              case 'error':
                currentRecord.error = data.content
                emits('error')
                break
              case 'predict-result':
                predict_answer += data.reasoning_content
                predict_content += data.content
                _currentChat.value.records[index.value].predict = predict_answer
                _currentChat.value.records[index.value].predict_content = predict_content
                break
              case 'predict-failed':
                emits('error')
                break
              case 'predict-success':
                //currentChat.value.records[_index].predict_data = data.content
                getChatPredictData(_currentChat.value.records[index.value].id)
                emits('finish', currentRecord.id)
                break
              case 'predict_finish':
                _loading.value = false
                break
            }
            await nextTick()
          }
        }
      }
    }
  } catch (error) {
    if (!currentRecord.error) {
      currentRecord.error = ''
    }
    if (currentRecord.error.trim().length !== 0) {
      currentRecord.error = currentRecord.error + '\n'
    }
    currentRecord.error = currentRecord.error + 'Error:' + error
    console.error('Error:', error)
    emits('error')
  } finally {
    _loading.value = false
  }
}

const chartBlockRef = ref()

const loadingData = ref(false)

function getChatPredictData(recordId?: number) {
  loadingData.value = true
  chatApi
    .get_chart_predict_data(recordId)
    .then((response) => {
      let has = false
      _currentChat.value.records.forEach((record) => {
        if (record.id === recordId) {
          has = true
          record.predict_data = response ?? []

          if (record.predict_data.length > 1) {
            getChatData(recordId)
          } else {
            loadingData.value = false
          }
        }
      })
      if (!has) {
        _loading.value = false
      }
    })
    .catch((e) => {
      loadingData.value = false
      console.error(e)
    })
}

function getChatData(recordId?: number) {
  loadingData.value = true
  chatApi
    .get_chart_data(recordId)
    .then((response) => {
      _currentChat.value.records.forEach((record) => {
        if (record.id === recordId) {
          record.data = response
        }
      })
    })
    .finally(() => {
      loadingData.value = false
      emits('scrollBottom')
    })
}

function stop() {
  stopFlag.value = true
  _loading.value = false
  emits('stop')
}

onBeforeUnmount(() => {
  stop()
})

onMounted(() => {
  if (props.message?.record?.id && props.message?.record?.finish) {
    getChatPredictData(props.message.record.id)
  }
})

defineExpose({ sendMessage, index: () => index.value, chatList: () => _chatList, stop })
</script>

<template>
  <BaseAnswer v-if="message" :message="message" :reasoning-name="['predict']" :loading="_loading">
    <MdComponent :message="message.record?.predict_content" style="margin-top: 12px" />
    <ChartBlock
      v-if="message.record?.predict_data?.length > 0 && message.record?.data"
      ref="chartBlockRef"
      style="margin-top: 12px"
      :record-id="recordId"
      :message="message"
      :loading-data="loadingData"
      is-predict
    />
    <slot></slot>
    <template #tool>
      <slot name="tool"></slot>
    </template>
    <template #footer>
      <slot name="footer"></slot>
    </template>
  </BaseAnswer>
</template>

<style scoped lang="less"></style>
