<script lang="ts" setup>
import { ref, shallowRef } from 'vue'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const chatSetting = ref({
  modelThinkingProcess: false,
  rows_of_data: false,
})

const platform = ref({
  organization: false,
  modelThinkingProcess: false,
  roles: [],
})

const organizations = shallowRef<any[]>([])
const roles = shallowRef<any[]>([])
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
            <el-switch v-model="chatSetting.modelThinkingProcess" />
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
            <el-switch v-model="chatSetting.rows_of_data" />
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          {{ t('parameter.third_party_platform_settings') }}
        </div>
        <div class="card-item" style="width: 100%">
          <div class="label">
            {{ t('parameter.by_third_party_platform') }}
          </div>
          <div class="value">
            <el-switch v-model="platform.modelThinkingProcess" />
          </div>
        </div>
        <div class="card-item">
          <div class="label">
            {{ t('parameter.platform_user_organization') }}
            <span class="require"></span>
            <el-tooltip
              effect="dark"
              :content="t('parameter.and_platform_integration')"
              placement="top"
            >
              <el-icon size="16">
                <icon_info_outlined_1></icon_info_outlined_1>
              </el-icon>
            </el-tooltip>
          </div>
          <div class="value">
            <el-select filterable v-model="platform.organization">
              <el-option
                v-for="item in organizations"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </div>
        <div class="card-item" style="margin-left: 16px">
          <div class="label">
            {{ t('parameter.platform_user_roles') }}
            <span class="require"></span>
            <el-tooltip
              effect="dark"
              :content="t('parameter.and_platform_integration')"
              placement="top"
            >
              <el-icon size="16">
                <icon_info_outlined_1></icon_info_outlined_1>
              </el-icon>
            </el-tooltip>
          </div>
          <div class="value">
            <el-select multiple filterable v-model="platform.roles">
              <el-option
                v-for="item in roles"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </div>
      </div>
    </div>
    <div class="save" style="margin-top: 16px">
      <el-button type="primary">{{ t('common.save') }}</el-button>
    </div>
  </div>
</template>

<style lang="less" scoped>
.parameter {
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
