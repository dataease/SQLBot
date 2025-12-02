<script lang="ts" setup>
import delIcon from '@/assets/svg/icon_delete.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_form_outlined from '@/assets/svg/icon_form_outlined.svg'
import icon_chat_outlined from '@/assets/svg/icon_new-chat_outlined.svg'
import { computed, ref, unref } from 'vue'
import { ClickOutside as vClickOutside } from 'element-plus-secondary'
import { dsTypeWithImg } from './js/ds-type'
import edit from '@/assets/svg/icon_edit_outlined.svg'
import icon_recommended_problem from '@/assets/svg/icon_recommended_problem.svg'
import { datasourceApi } from '@/api/datasource.ts'

const props = withDefaults(
  defineProps<{
    name: string
    type: string
    typeName: string
    num: string
    description?: string
    id?: string
  }>(),
  {
    name: '-',
    type: '-',
    description: '-',
    id: '-',
    typeName: '-',
  }
)

const emits = defineEmits([
  'edit',
  'del',
  'question',
  'dataTableDetail',
  'showTable',
  'recommendation',
])
const icon = computed(() => {
  return (dsTypeWithImg.find((ele) => props.type === ele.type) || {}).img
})
const handleEdit = () => {
  emits('edit')
}

const handleRecommendation = () => {
  emits('recommendation')
}

const handleDel = () => {
  emits('del')
}

const handleQuestion = () => {
  //check first
  datasourceApi.check_by_id(props.id).then((res: any) => {
    if (res) {
      emits('question', props.id)
    }
  })
}

function runSQL() {
  datasourceApi.execSql(
    props.id,
    'SELECT TO_CHAR(FLOOR("c"."CREDIT_LIMIT" / 10000) * 10000) || \' - \' || TO_CHAR((FLOOR("c"."CREDIT_LIMIT" / 10000) + 1) * 10000) AS "credit_range",\n' +
      '       COUNT(*) AS "customer_count"\n' +
      'FROM "WEI"."CUSTOMERS" "c"\n' +
      'WHERE "c"."CREDIT_LIMIT" IS NOT NULL\n' +
      'GROUP BY FLOOR("c"."CREDIT_LIMIT" / 10000)\n' +
      'ORDER BY FLOOR("c"."CREDIT_LIMIT" / 10000)'
  )
}

const dataTableDetail = () => {
  emits('dataTableDetail')
}
const buttonRef = ref()
const popoverRef = ref()
const onClickOutside = () => {
  unref(popoverRef).popperRef?.delayHide?.()
}
</script>

<template>
  <div class="card" @click="dataTableDetail">
    <div class="name-icon">
      <img :src="icon" width="32px" height="32px" />
      <div class="info">
        <div :title="name" class="name ellipsis">{{ name }}</div>
        <div class="type">{{ typeName }}</div>
      </div>
    </div>
    <div :title="description" class="type-value">
      {{ description }}
    </div>

    <div class="bottom-info">
      <div class="form-rate">
        <el-icon class="form-icon" size="16">
          <icon_form_outlined></icon_form_outlined>
        </el-icon>
        {{ num }}
      </div>
      <div click.stop class="methods">
        <el-button v-if="false" @click="runSQL">test</el-button>
        <el-button type="primary" style="margin-right: 8px" @click.stop="handleQuestion">
          <el-icon style="margin-right: 4px" size="16">
            <icon_chat_outlined></icon_chat_outlined>
          </el-icon>
          {{ $t('datasource.open_query') }}
        </el-button>
        <el-icon
          ref="buttonRef"
          v-click-outside="onClickOutside"
          class="more"
          size="16"
          style="color: #646a73"
          @click.stop
        >
          <icon_more_outlined></icon_more_outlined>
        </el-icon>
        <el-popover
          ref="popoverRef"
          :virtual-ref="buttonRef"
          virtual-triggering
          trigger="click"
          :teleported="false"
          popper-class="popover-card_ds"
          placement="bottom-end"
        >
          <div class="content">
            <div class="item" @click.stop="handleEdit">
              <el-icon size="16">
                <edit></edit>
              </el-icon>
              {{ $t('datasource.edit') }}
            </div>
            <div class="item" @click.stop="handleRecommendation">
              <el-icon size="16">
                <icon_recommended_problem></icon_recommended_problem>
              </el-icon>
              {{ $t('datasource.recommended_problem_configuration') }}
            </div>
            <div class="item" @click.stop="handleDel">
              <el-icon size="16">
                <delIcon></delIcon>
              </el-icon>
              {{ $t('dashboard.delete') }}
            </div>
          </div>
        </el-popover>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.card {
  width: 100%;
  border: 1px solid #dee0e3;
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;

  &:hover {
    box-shadow: 0px 6px 24px 0px #1f232914;
  }

  .name-icon {
    display: flex;
    align-items: center;
    margin-bottom: 12px;

    .info {
      margin-left: 12px;
      max-width: calc(100% - 50px);

      .name {
        font-weight: 500;
        font-size: 16px;
        line-height: 24px;
        max-width: 100%;
      }

      .type {
        font-weight: 400;
        font-size: 12px;
        line-height: 20px;
        color: #646a73;
      }
    }
  }

  .type-value {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    color: #646a73;
    height: 44px;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    word-break: break-word;
    overflow: hidden;
    width: 100%;
  }

  .bottom-info {
    margin-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;

    .form-rate {
      display: flex;
      align-items: center;
      color: #646a73;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;

      .form-icon {
        margin-right: 8px;
      }
    }

    .methods {
      align-items: center;
      display: none;

      .more {
        position: relative;
        cursor: pointer;
        margin-left: 4px;
        width: 32px;
        height: 32px;

        svg {
          position: relative;
          z-index: 10;
        }

        &::after {
          content: '';
          position: absolute;
          border-radius: 6px;
          width: 32px;
          height: 32px;
          transform: translate(-50%, -50%);
          top: 50%;
          left: 50%;
          background: #fff;
          border: 1px solid #d9dcdf;
        }

        &:hover {
          &::after {
            background-color: #f5f6f7;
          }
        }
      }
    }
  }

  &:hover {
    .methods {
      display: flex;
    }
  }
}
</style>

<style lang="less">
.popover-card_ds.popover-card_ds.popover-card_ds {
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border-radius: 4px;
  border: 1px solid #dee0e3;
  width: fit-content !important;
  min-width: 120px !important;
  padding: 0;

  .content {
    position: relative;

    &::after {
      position: absolute;
      content: '';
      top: 80px !important;
      left: 0;
      width: 100%;
      height: 1px;
      background: #dee0e3;
    }

    .item {
      position: relative;
      padding: 0 12px;
      height: 40px;
      display: flex;
      align-items: center;
      cursor: pointer;

      .ed-icon {
        margin-right: 8px;
        color: #646a73;
      }

      &:hover {
        &::after {
          display: block;
        }
      }

      &::after {
        content: '';
        width: calc(100% - 8px);
        height: 32px;
        border-radius: 4px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1f23291a;
        display: none;
      }
    }
  }
}
</style>
