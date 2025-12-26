<script lang="ts" setup>
import { onMounted, provide, reactive, unref } from 'vue'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'
import { useI18n } from 'vue-i18n'
import PlatformParam from './xpack/PlatformParam.vue'
import { request } from '@/utils/request'
import { formatArg } from '@/utils/utils'
const { t } = useI18n()

const state = reactive({
  parameterForm: reactive<any>({
    'chat.expand_thinking_block': false,
    'chat.limit_rows': false,
  }),
})
provide('parameterForm', state.parameterForm)
const loadData = () => {
  request.get('/system/parameter').then((res: any) => {
    if (res) {
      res.forEach((item: any) => {
        if (
          item.pkey?.startsWith('chat') ||
          item.pkey?.startsWith('login') ||
          item.pkey?.startsWith('platform')
        ) {
          state.parameterForm[item.pkey] = formatArg(item.pval)
        }
      })
      console.log(state.parameterForm)
    }
  })
}

const beforeChange = (): Promise<boolean> => {
  return new Promise((resolve) => {
    if (!state.parameterForm['chat.rows_of_data']) {
      return resolve(true)
    }
    ElMessageBox.confirm(t('parameter.excessive_data_volume'), t('parameter.prompt'), {
      confirmButtonType: 'primary',
      confirmButtonText: t('common.confirm2'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon confirm_no_icon_parameter',
      autofocus: false,
      callback: (action: any) => {
        resolve(action && action === 'confirm')
      },
    })
  })
}
const buildParam = () => {
  const changedItemArray = Object.keys(state.parameterForm).map((key: string) => {
    return {
      pkey: key,
      pval: Object.prototype.hasOwnProperty.call(state.parameterForm, 'key')
        ? state.parameterForm[key].toString()
        : state.parameterForm[key],
    }
  })
  const formData = new FormData()
  formData.append('data', JSON.stringify(unref(changedItemArray)))
  return formData
}
const saveHandler = () => {
  const param = buildParam()
  request
    .post('/system/parameter', param, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    .then(() => {
      ElMessage.success(t('common.save_success'))
    })
}
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="parameter">
    <div class="title">
      {{ t('parameter.parameter_configuration') }}
    </div>
    <div class="card-container">
      <div class="card">
        <div class="card-title">
          {{ t('parameter.question_count_settings') }}
        </div>
        <div class="card-item">
          <div class="label">
            {{ t('parameter.model_thinking_process') }}

            <el-tooltip effect="dark" :content="t('parameter.closed_by_default')" placement="top">
              <el-icon size="16">
                <icon_info_outlined_1></icon_info_outlined_1>
              </el-icon>
            </el-tooltip>
          </div>
          <div class="value">
            <el-switch v-model="state.parameterForm['chat.expand_thinking_block']" />
          </div>
        </div>

        <div class="card-item" style="margin-left: 16px">
          <div class="label">
            {{ t('parameter.rows_of_data') }}
            <el-tooltip
              effect="dark"
              :content="t('parameter.excessive_data_volume')"
              placement="top"
            >
              <el-icon size="16">
                <icon_info_outlined_1></icon_info_outlined_1>
              </el-icon>
            </el-tooltip>
          </div>
          <div class="value">
            <el-switch
              v-model="state.parameterForm['chat.limit_rows']"
              :before-change="beforeChange"
            />
          </div>
        </div>
      </div>

      <platform-param />
    </div>
    <div class="save" style="margin-top: 16px">
      <el-button type="primary" @click="saveHandler">{{ t('common.save') }}</el-button>
    </div>
  </div>
</template>
<style lang="less">
.confirm_no_icon_parameter {
  .ed-message-box__header {
    margin-bottom: var(--ed-messagebox-padding-primary);
  }
  .ed-message-box__message > p {
    font-size: 14px;
    font-weight: 400;
    line-height: 22px;
  }
}
</style>
<style lang="less" scoped>
.parameter {
  :deep(.ed-radio) {
    --ed-radio-input-height: 16px;
    --ed-radio-input-width: 16px;
  }
  .title {
    font-weight: 500;
    font-style: Medium;
    font-size: 20px;
    line-height: 28px;
    margin-bottom: 16px;
  }
  .card-container {
    .card {
      width: 100%;
      border-radius: 12px;
      padding: 16px;
      border: 1px solid #dee0e3;
      display: flex;
      flex-wrap: wrap;
      margin-top: 16px;

      .card-title {
        font-weight: 500;
        font-style: Medium;
        font-size: 16px;
        line-height: 24px;
        width: 100%;
      }
      .card-item {
        margin-top: 16px;
        width: calc(50% - 8px);
        .label {
          font-weight: 400;
          font-size: 14px;
          line-height: 22px;
          display: flex;
          align-items: center;

          .ed-icon {
            margin-left: 4px;
          }

          .require::after {
            content: '*';
            color: var(--ed-color-danger);
            margin-left: 4px;
          }
        }

        .value {
          margin-top: 8px;
          line-height: 20px;
        }
      }
    }
  }
}
</style>
