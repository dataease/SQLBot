import JSONBig from 'json-bigint'
import { chatApi, type ChatInfo, questionApi } from '@/api/chat.ts'

export type RunQuestionStreamOptions = {
  currentChat: ChatInfo
  chatList: ChatInfo[]
  chatId: number
  recordIndex: number
  shouldAbort?: () => boolean
  getChartData?: (recordId?: number) => void
  onFinish?: (recordId?: number) => void
  onError?: (recordId?: number) => void
  scrollBottom?: () => void
}

function defaultGetChartData(recordId: number | undefined, currentChat: ChatInfo, scrollBottom?: () => void) {
  if (!recordId) return
  chatApi.get_chart_data(recordId).then((response) => {
    currentChat.records.forEach((record) => {
      if (record.id === recordId) {
        record.data = response
      }
    })
    scrollBottom?.()
  })
}

/**
 * 与 ChartAnswer.sendMessage 相同的流式问数逻辑；可由父组件直接调用，避免依赖子组件 ref 挂载时机。
 */
export async function runQuestionStream(options: RunQuestionStreamOptions): Promise<void> {
  const {
    currentChat,
    chatList,
    chatId,
    recordIndex,
    shouldAbort,
    getChartData = (rid) => defaultGetChartData(rid, currentChat, options.scrollBottom),
    onFinish,
    onError,
    scrollBottom,
  } = options

  const currentRecord = currentChat.records[recordIndex]
  if (!currentRecord || !currentRecord.question?.trim()) {
    return
  }

  try {
    const controller = new AbortController()
    const param = {
      question: currentRecord.question,
      chat_id: chatId,
    }
    const response = await questionApi.add(param, controller)
    const reader = response.body!.getReader()
    const decoder = new TextDecoder('utf-8')

    let sql_answer = ''
    let chart_answer = ''
    let tempResult = ''
    let abortedByUser = false

    while (true) {
      if (shouldAbort?.()) {
        controller.abort()
        abortedByUser = true
        break
      }
      const { done, value } = await reader.read()
      if (done) {
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
              data = JSONBig.parse(str.replace('data:{', '{'))
            } catch (err) {
              console.error('JSON string:', str)
              throw err
            }

            if (data.code && data.code !== 200) {
              throw new Error(data.msg || String(data))
            }

            switch (data.type) {
              case 'id':
                currentRecord.id = data.id
                currentChat.records[recordIndex].id = data.id
                break
              case 'regenerate_record_id':
                currentRecord.regenerate_record_id = data.regenerate_record_id
                currentChat.records[recordIndex].regenerate_record_id = data.regenerate_record_id
                break
              case 'question':
                currentRecord.question = data.question
                currentChat.records[recordIndex].question = data.question
                break
              case 'info':
                console.info(data.msg)
                break
              case 'brief':
                currentChat.brief = data.brief
                chatList.forEach((c) => {
                  if (c.id === currentChat.id) {
                    c.brief = currentChat.brief
                  }
                })
                break
              case 'error':
                currentRecord.error = data.content
                onError?.(currentRecord.id)
                break
              case 'sql-result':
                sql_answer += data.reasoning_content
                currentChat.records[recordIndex].sql_answer = sql_answer
                break
              case 'sql':
                currentChat.records[recordIndex].sql = data.content
                break
              case 'sql-data':
                getChartData(currentChat.records[recordIndex].id)
                break
              case 'chart-result':
                chart_answer += data.reasoning_content
                currentChat.records[recordIndex].chart_answer = chart_answer
                break
              case 'chart':
                currentChat.records[recordIndex].chart = data.content
                break
              case 'datasource':
                if (!currentChat.datasource) {
                  currentChat.datasource = data.id
                }
                break
              case 'finish':
                onFinish?.(currentRecord.id)
                break
            }
            await Promise.resolve()
          }
        }
      }
    }

    if (abortedByUser) {
      onError?.(currentRecord.id)
      return
    }
  } catch (error: any) {
    console.error('runQuestionStream:', error)
    onError?.(currentRecord.id)
    throw error
  }
}
