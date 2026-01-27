<script lang="ts">
import icon_down_outlined from '@/assets/svg/arrow-down.svg'
import icon_close_outlined_w from '@/assets/svg/icon_close_outlined_12.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
export default {
  name: 'LogicRelation',
}
</script>
<script lang="ts" setup>
import { useI18n } from 'vue-i18n'
import { type PropType, computed, toRefs } from 'vue'
import FilterFiled from './FilterFiled.vue'
import type { Item } from './FilterFiled.vue'
export type Logic = 'or' | 'and'
export type Relation = {
  child?: Relation[]
  logic: Logic
  x: number
} & Item
const { t } = useI18n()

const props = defineProps({
  relationList: {
    type: Array as PropType<Relation[]>,
    default: () => [],
  },
  x: {
    type: Number,
    default: 0,
  },
  logic: {
    type: String as PropType<Logic>,
    default: 'or',
  },
})

const marginLeft = computed(() => {
  return {
    marginLeft: props.x ? '20px' : 0,
  }
})

const emits = defineEmits([
  'addCondReal',
  'changeAndOrDfs',
  'update:logic',
  'removeRelationList',
  'del',
])

const { relationList } = toRefs(props)

const handleCommand = (type: any) => {
  emits('update:logic', type)
  emits('changeAndOrDfs', type)
}

const removeRelationList = (index: any) => {
  relationList.value.splice(index, 1)
}
const addCondReal = (type: any) => {
  emits('addCondReal', type, props.logic === 'or' ? 'and' : 'or')
}
const add = (type: any, child: any, logic: any) => {
  child.push(
    type === 'condition'
      ? {
          field_id: '',
          value: '',
          enum_value: '',
          term: '',
          filter_type: 'logic',
          name: '',
          value_type: 'normal',
          variable_id: undefined,
        }
      : { child: [], logic }
  )
}
const del = (index: any, child: any) => {
  child.splice(index, 1)
}
</script>

<template>
  <div class="logic" :style="marginLeft">
    <div class="logic-left">
      <div class="operate-title">
        <span v-if="x" class="mrg-title">
          {{ logic === 'or' ? 'OR' : 'AND' }}
        </span>
        <el-dropdown v-else trigger="click" @command="handleCommand">
          <span class="mrg-title">
            {{ logic === 'or' ? 'OR' : 'AND' }}
            <el-icon size="12">
              <icon_down_outlined />
            </el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="and">AND</el-dropdown-item>
              <el-dropdown-item command="or">OR</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <span v-if="x" class="operate-icon">
        <el-icon size="12" @click="emits('removeRelationList')">
          <icon_close_outlined_w />
        </el-icon>
      </span>
    </div>
    <div class="logic-right">
      <template v-for="(item, index) in relationList" :key="index">
        <logic-relation
          v-if="item.child"
          :x="item.x"
          :logic="item.logic"
          :relation-list="item.child"
          @del="(idx) => del(idx, item.child)"
          @add-cond-real="(type, logic) => add(type, item.child, logic)"
          @remove-relation-list="removeRelationList(index)"
        >
        </logic-relation>
        <filter-filed v-else :item="item" :index="index" @del="emits('del', index)"></filter-filed>
      </template>
      <div class="logic-right-add">
        <button class="operand-btn" @click="addCondReal('condition')">
          <el-icon style="margin-right: 4px" size="16">
            <icon_add_outlined></icon_add_outlined>
          </el-icon>
          {{ t('permission.add_conditions') }}
        </button>
        <button v-if="x < 2" class="operand-btn" @click="addCondReal('relation')">
          <el-icon style="margin-right: 4px" size="16">
            <icon_add_outlined></icon_add_outlined>
          </el-icon>
          {{ t('permission.add_relationships') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.logic {
  display: flex;
  align-items: center;
  position: relative;
  z-index: 1;
  width: 100%;

  .logic-left {
    box-sizing: border-box;
    width: 48px;
    display: flex;
    position: relative;
    align-items: center;
    z-index: 10;
    background: #fff;
    width: 48px;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    &::after {
      width: 100%;
      height: 100%;
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #1f23291a;
      z-index: 1;
      border-radius: 4px;
      user-select: none;
      pointer-events: none;
    }

    .operate-title {
      word-wrap: break-word;
      box-sizing: border-box;
      color: rgba(0, 0, 0, 0.65);
      font-size: 12px;
      display: inline-block;
      white-space: nowrap;
      margin: 0;
      padding: 0;
      line-height: 20px;
      position: relative;
      z-index: 1;
      height: 20px;
      color: #1f2329;

      .mrg-title {
        text-align: left;
        box-sizing: border-box;
        position: relative;
        display: flex;
        height: 20px;
        font-size: 12px;
        align-items: center;
        justify-content: center;
      }
    }

    &:hover {
      .operate-icon {
        display: inline-block;
      }

      .mrg-title {
        margin-right: 0;
      }
    }

    .operate-icon {
      height: 20px;
      line-height: 20px;
      z-index: 1;
    }
  }

  .logic-right-add {
    display: flex;
    height: 41.4px;
    align-items: center;
    padding-left: 26px;

    .operand-btn {
      box-sizing: border-box;
      font-weight: 400;
      text-align: center;
      outline: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: 1;
      cursor: pointer;
      height: 32px;
      padding: 0 10px;
      margin-right: 10px;
      font-size: 14px;
      color: var(--ed-color-primary);
      background: #fff;
      border: 1px solid var(--ed-color-primary);
      border-radius: 6px;
    }
  }
}
</style>
