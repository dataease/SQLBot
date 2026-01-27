<script lang="ts" setup>
import icon_deleteTrash_outlined from '@/assets/svg/icon_delete.svg'
import { ref, inject, computed, onBeforeMount, toRefs, type Ref, shallowRef } from 'vue'
import { variablesApi } from '@/api/variables'
import { useI18n } from 'vue-i18n'
import { allOptions } from '../options'
export interface Item {
  term: string
  field_id: string
  filter_type: string
  enum_value: string
  name: string
  value: any
  value_type: any
  variable_id: any
}

export interface sysVariable {
  label: string
  value: string
  type: string
}

type Props = {
  index: number
  item: Item
}

const props = withDefaults(defineProps<Props>(), {
  index: 0,
  item: () => ({
    term: '',
    field_id: '',
    filter_type: '',
    enum_value: '',
    name: '',
    value: null,
    value_type: 'normal',
    variable_id: undefined,
  }),
})

const { t } = useI18n()
const showDel = ref(false)
const keywords = ref('')
const activeName = ref()
const checklist = ref<string[]>([])
const filterList = ref<any[]>([])
const variables = shallowRef<any[]>([])
const valueTypeList = [
  {
    value: 'normal',
    label: t('variables.normal_value'),
  },
  {
    value: 'variable',
    label: t('variables.system_variables'),
  },
]
const { item } = toRefs(props)

const filedList = inject('filedList') as Ref<any[]>

const computedWidth = computed(() => {
  const { field_id } = item.value
  return {
    width: !field_id ? '270px' : '770px',
  }
})

const operators = computed(() => {
  return allOptions
})

const computedFiledList = computed<any[]>(() => {
  return filedList.value || []
})

const dimensions = computed(() => {
  if (!keywords.value) return computedFiledList.value
  return computedFiledList.value.filter((ele) => ele.name.includes(keywords.value))
})

onBeforeMount(() => {
  initNameEnumName()
  filterListInit()
  getVariables()
})

const getVariables = () => {
  variablesApi.listAll().then((res: any) => {
    variables.value = res || []
  })
}

const initNameEnumName = () => {
  const { name, enum_value, field_id } = item.value
  dimensions.value.forEach((ele) => {
    if (+ele.id === +field_id) {
      activeName.value = ele
    }
  })
  const arr = enum_value.trim() ? enum_value.split(',') : []
  if (!name && field_id) {
    checklist.value = arr
  }
  if (!name && !field_id) return
  initEnumOptions()
  checklist.value = arr
}

const filterTypeChange = () => {
  item.value.term = ''
  item.value.value = null
  initEnumOptions()
}
const initEnumOptions = () => {
  console.info('initEnumOptions')
}

const selectItem = ({ field_name, id }: any) => {
  Object.assign(item.value, {
    field_id: id,
    name: field_name,
    filter_type: 'logic',
    value: '',
    term: '',
    variable_id: undefined,
    value_type: 'normal',
  })
  filterListInit()
  checklist.value = []
}

const filterListInit = () => {
  filterList.value = [
    {
      value: 'logic',
      label: t('permission.conditional_filtering'),
    },
  ]
}

const emits = defineEmits(['update:item', 'del'])
</script>

<template>
  <div class="white-nowrap">
    <div
      class="filed"
      :style="computedWidth"
      @mouseover="showDel = true"
      @mouseleave="showDel = false"
    >
      <el-select
        v-model="activeName"
        value-key="id"
        :placeholder="$t('permission.conditional_filtering')"
        style="width: 200px"
        @change="selectItem"
      >
        <el-option v-for="ele in dimensions" :key="ele.id" :label="ele.field_name" :value="ele" />
      </el-select>
      <template v-if="item.field_id">
        <el-select
          v-model="item.filter_type"
          style="width: 120px; margin-left: 8px"
          :placeholder="$t('permission.conditional_filtering')"
          @change="filterTypeChange"
        >
          <el-option
            v-for="ele in filterList"
            :key="ele.value"
            :label="ele.label"
            :value="ele.value"
          >
          </el-option>
        </el-select>
        <el-select
          v-model="item.value_type"
          style="width: 102px; margin-left: 8px"
          :placeholder="$t('permission.conditional_filtering')"
          @change="filterTypeChange"
        >
          <el-option
            v-for="ele in valueTypeList"
            :key="ele.value"
            :label="ele.label"
            :value="ele.value"
          >
          </el-option>
        </el-select>
        <el-select
          v-if="['null', 'not_null', 'empty', 'not_empty'].includes(item.term)"
          v-model="item.term"
          style="max-width: 280px; margin-left: 8px"
          :placeholder="t('datasource.Please_select')"
        >
          <el-option
            v-for="ele in operators"
            :key="ele.value"
            :label="t(ele.label)"
            :value="ele.value"
          >
          </el-option>
        </el-select>
        <el-input
          v-else-if="item.value_type === 'normal'"
          v-model="item.value"
          style="max-width: 280px; margin-left: 8px"
          :placeholder="$t('datasource.please_enter')"
          class="input-with-select"
          clearable
        >
          <template #prepend>
            <el-select
              v-model="item.term"
              style="width: 75px"
              :placeholder="t('datasource.Please_select')"
            >
              <el-option
                v-for="ele in operators"
                :key="ele.value"
                :label="t(ele.label)"
                :value="ele.value"
              >
              </el-option>
            </el-select>
          </template>
        </el-input>
        <template v-else>
          <el-select
            v-model="item.term"
            style="width: 75px; margin-left: 8px"
            :placeholder="t('datasource.Please_select')"
          >
            <el-option
              v-for="ele in operators"
              :key="ele.value"
              :label="t(ele.label)"
              :value="ele.value"
            >
            </el-option>
          </el-select>
          <el-select
            v-model="item.variable_id"
            style="max-width: 197px; margin-left: 8px"
            :placeholder="t('datasource.Please_select')"
          >
            <el-option v-for="ele in variables" :key="ele.id" :label="ele.name" :value="ele.id">
            </el-option>
          </el-select>
        </template>
      </template>
      <el-icon v-if="showDel" class="font16" @click="emits('del')">
        <icon_deleteTrash_outlined />
      </el-icon>
    </div>
  </div>
</template>

<style lang="less" scoped>
.white-nowrap {
  white-space: nowrap;
}
.filed {
  height: 41.4px;
  padding: 1px 3px 1px 0;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  margin-left: 20px;
  min-width: 200px;
  justify-content: left;
  position: relative;
  white-space: nowrap;

  .filed-title {
    word-wrap: break-word;
    line-height: 28px;
    color: #7e7e7e;
    font-size: 14px;
    white-space: nowrap;
    box-sizing: border-box;
    margin-right: 5px;
    display: inline-block;
    min-width: 50px;
    text-align: right;
  }

  .font16 {
    font-size: 16px;
    margin: 0 10px;
    cursor: pointer;
  }

  :deep(.ed-input-group__prepend) {
    background-color: #fff;
  }
}
</style>
