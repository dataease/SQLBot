<script lang="ts" setup>
import { ref, onMounted, onUnmounted } from 'vue'
import icon_expand_right_filled from '@/assets/svg/icon_expand-right_filled.svg'
import gou_icon from '@/assets/svg/gou_icon.svg'
import icon_error from '@/assets/svg/icon_error.svg'
import icon_database_colorful from '@/assets/svg/icon_database_colorful.svg'
import icon_alarm_clock_colorful from '@/assets/svg/icon_alarm-clock_colorful.svg'
import { chatApi, type ChatLogHistory } from '@/api/chat.ts'
import { useI18n } from 'vue-i18n'
import { debounce } from 'lodash-es'
import LogTerm from './execution-component/LogTerm.vue'
import LogSQLSample from './execution-component/LogSQLSample.vue'
import LogCustomPrompt from './execution-component/LogCustomPrompt.vue'
import LogDataQuery from './execution-component/LogDataQuery.vue'
import LogChooseTable from './execution-component/LogChooseTable.vue'
import LogGeneratePicture from './execution-component/LogGeneratePicture.vue'
import LogWithAi from '@/views/chat/execution-component/LogWithAi.vue'

const { t } = useI18n()
const logHistory = ref<ChatLogHistory>({})
const dialogFormVisible = ref(false)
const expandIds = ref<any>([])
const drawerSize = ref('600px')

const handleExpand = (index: number) => {
  if (expandIds.value.includes(index)) {
    expandIds.value = expandIds.value.filter((ele: any) => ele !== index)
  } else {
    expandIds.value.push(index)
  }
}

function getLogList(recordId: any) {
  setDrawerSize()
  chatApi.get_chart_log_history(recordId).then((res) => {
    logHistory.value = chatApi.toChatLogHistory(res) as ChatLogHistory
    dialogFormVisible.value = true
  })
}

const setDrawerSize = debounce(() => {
  drawerSize.value = window.innerWidth < 500 ? '460px' : '600px'
}, 500)

onMounted(() => {
  window.addEventListener('resize', setDrawerSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', setDrawerSize)
})

defineExpose({
  getLogList,
})
</script>

<template>
  <el-drawer
    v-model="dialogFormVisible"
    :title="t('parameter.execution_details')"
    destroy-on-close
    modal-class="execution-details"
    :size="drawerSize"
  >
    <div class="title">{{ t('parameter.overview') }}</div>
    <div class="overview">
      <div class="item">
        <el-icon size="40">
          <icon_database_colorful></icon_database_colorful>
        </el-icon>
        <div class="name">{{ t('parameter.tokens_required') }}</div>
        <div class="value">{{ logHistory.total_tokens }}</div>
      </div>
      <div class="item">
        <el-icon size="40">
          <icon_alarm_clock_colorful></icon_alarm_clock_colorful>
        </el-icon>
        <div class="name">{{ t('parameter.time_execution') }}</div>
        <div class="value">{{ logHistory.duration }}s</div>
      </div>
    </div>
    <div class="title">{{ t('parameter.execution_details') }}</div>

    <div class="list">
      <div v-for="(ele, index) in logHistory.steps" :key="ele.duration" class="list-item">
        <div class="header" @click="handleExpand(index)">
          <div class="name">
            <el-icon class="shrink" :class="expandIds.includes(index) && 'expand'" size="10">
              <icon_expand_right_filled></icon_expand_right_filled>
            </el-icon>
            {{ ele.operate }}
          </div>
          <div class="status">
            <div
              v-if="ele.total_tokens && ele.total_tokens > 0"
              class="time"
              style="margin-right: 12px"
            >
              {{ ele.total_tokens }} tokens
            </div>
            <div class="time">{{ ele.duration }}s</div>
            <el-icon size="16">
              <icon_error v-if="ele.error"></icon_error>
              <gou_icon v-else></gou_icon>
            </el-icon>
          </div>
        </div>
        <div v-if="expandIds.includes(index)" class="content">
          <LogTerm v-if="ele.operate_key === 'FILTER_TERMS'" :item="ele" />
          <LogSQLSample v-else-if="ele.operate_key === 'FILTER_SQL_EXAMPLE'" :item="ele" />
          <LogCustomPrompt v-else-if="ele.operate_key === 'FILTER_CUSTOM_PROMPT'" :item="ele" />
          <LogChooseTable v-else-if="ele.operate_key === 'CHOOSE_TABLE'" :item="ele" />
          <LogDataQuery v-else-if="ele.operate_key === 'EXECUTE_SQL'" :item="ele" />
          <LogGeneratePicture v-else-if="ele.operate_key === 'GENERATE_PICTURE'" :item="ele" />
          <LogWithAi v-else :item="ele" />
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<style lang="less">
.execution-details {
  .title {
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
    margin-bottom: 16px;
  }

  .overview {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    .item {
      width: calc(50% - 8px);
      height: 86px;
      border-radius: 12px;
      border: 1px solid #dee0e3;
      padding: 16px;

      .ed-icon {
        float: left;
        margin: 8px 12px 0 0;
      }

      .name {
        float: left;
        color: #646a73;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        width: 64%;
      }

      .value {
        float: left;
        font-weight: 500;
        font-size: 20px;
        line-height: 28px;
        color: #1f2329;
        margin-top: 4px;
      }
    }
  }

  .list {
    .list-item {
      width: 100%;
      border-radius: 12px;
      border: 1px solid #dee0e3;
      padding: 16px;
      margin-bottom: 8px;

      .header {
        display: flex;
        align-items: center;
      }

      @keyframes expand {
        0% {
          height: 54px;
        }

        100% {
          min-height: 54px;
        }
      }

      &:has(.expand) {
        min-height: 54px;
        //animation: expand 0.5s;
      }

      .shrink {
        margin-right: 8px;
        cursor: pointer;
      }

      .expand {
        transform: rotate(90deg);
      }

      .status {
        display: flex;
        align-items: center;
        margin-left: auto;
      }
      .name {
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
        display: flex;
        align-items: center;
      }

      .time {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #646a73;
      }

      .ed-icon {
        margin-left: 12px;
      }
    }
  }
}
</style>
