<script lang="ts" setup>
import { ref, computed, reactive, provide, nextTick } from 'vue'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import icon_down_outlined from '@/assets/svg/icon_down_outlined.svg'
import ICON_TABLE from '@/assets/svg/chart/icon_form_outlined.svg'
import Card from './Card.vue'
import { dsTypeWithImg } from '@/views/ds/js/ds-type'
import SelectPermission from './SelectPermission.vue'
import AuthTree from './auth-tree/RowAuth.vue'
import { getList, savePermissions, delPermissions } from '@/api/permissions'
import { datasourceApi } from '@/api/datasource'
import { useI18n } from 'vue-i18n'
import { cloneDeep } from 'lodash-es'

const { t } = useI18n()
const keywords = ref('')
const activeStep = ref(0)
const dialogFormVisible = ref(false)
const ruleConfigvVisible = ref(false)
const editRule = ref(0)
const termFormRef = ref()
const columnFormRef = ref()
const drawerTitle = ref('')
const dialogTitle = ref('')
const activeDs = ref(null)
const activeTable = ref(null)
const ruleList = ref<any[]>([])

const defaultPermission = {
  id: '',
  name: '',
  permissions: [],
  users: [],
}
const currentPermission = reactive<any>(cloneDeep(defaultPermission))

const searchColumn = ref('')
const isCreate = ref(false)
const defaultForm = {
  name: '',
  id: '',
  table_id: '',
  type: 'row',
  ds_id: '',
  table_name: '',
  ds_name: '',
  permissions: [] as any[],
  expression_tree: {},
}
const columnForm = reactive(cloneDeep(defaultForm))
const selectPermissionRef = ref()
const tableListOptions = ref<any[]>([])
const fieldListOptions = ref<any[]>([])
const dsListOptions = ref<any[]>([])
const ruleListWithSearch = computed(() => {
  if (!keywords.value) return ruleList.value
  return ruleList.value.filter((ele) =>
    ele.name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})
const tableColumnData = computed<any[]>(() => {
  if (!searchColumn.value) return columnForm.permissions
  return columnForm.permissions.filter((ele) =>
    ele.field_name.toLowerCase().includes(searchColumn.value.toLowerCase())
  )
})
provide('filedList', fieldListOptions)
const setDrawerTitle = () => {
  if (activeStep.value === 0 && isCreate.value) {
    drawerTitle.value = t('permission.add_rule_group')
  } else {
    if (editRule.value === 1) {
      drawerTitle.value = t('permission.set_permission_rule')
    }

    if (editRule.value === 2) {
      drawerTitle.value = t('permission.select_restricted_user')
    }
  }
}

const userTypeList = [
  {
    name: t('permission.row_permission'),
    value: 1,
  },
  {
    name: t('permission.column_permission'),
    value: 0,
  },
]
const ruleType = ref(0)
const handleAddPermission = (val: any) => {
  ruleType.value = val
  Object.assign(columnForm, cloneDeep(defaultForm))
  if (val === 1) {
    handleRowPermission(null)
  } else {
    handleColumnPermission(null)
  }
}
const saveAuthTree = (val: any) => {
  if (val.errorMessage) {
    ElMessage.error(val.errorMessage)
    return
  }
  delete val.errorMessage
  columnForm.expression_tree = cloneDeep(val)
  const { expression_tree, table_id, ds_id, type, name, ds_name, table_name } = columnForm
  if (columnForm.id) {
    for (const key in currentPermission.permissions) {
      if (currentPermission.permissions[key].id === columnForm.id) {
        Object.assign(
          currentPermission.permissions[key],
          cloneDeep({
            expression_tree,
            tree: expression_tree,
            table_id,
            ds_id,
            type,
            name,
            ds_name,
            table_name,
          })
        )
      }
    }
  } else {
    currentPermission.permissions.push(
      cloneDeep({
        expression_tree,
        tree: expression_tree,
        table_id,
        ds_id,
        type,
        name,
        ds_name,
        table_name,
        id: +new Date(),
      })
    )
  }
  dialogFormVisible.value = false
}
const getDsList = (row: any) => {
  activeDs.value = null
  activeTable.value = null
  datasourceApi
    .list()
    .then((res: any) => {
      dsListOptions.value = res || []
      if (!row?.ds_id) return
      dsListOptions.value.forEach((ele) => {
        if (+ele.id === +row.ds_id) {
          activeDs.value = ele
        }
      })
    })
    .finally(() => {
      if (!row && columnForm.type === 'row') {
        authTreeRef.value.init(columnForm.expression_tree)
      }
    })

  if (row) {
    handleDsIdChange({ id: row.ds_id, name: row.ds_name })
    handleEditeTable(row.table_id)
  }
}
const handleRowPermission = (row: any) => {
  columnForm.type = 'row'
  getDsList(row)
  if (row) {
    const { name, ds_id, table_id, tree, id, ds_name, table_name } = row
    Object.assign(columnForm, {
      id,
      name,
      ds_id,
      table_id,
      ds_name,
      table_name,
      expression_tree: typeof tree === 'object' ? tree : JSON.parse(tree),
    })
  }
  dialogFormVisible.value = true
  dialogTitle.value = row?.id
    ? t('permission.edit_row_permission')
    : t('permission.add_row_permission')
}
const handleColumnPermission = (row: any) => {
  columnForm.type = 'column'
  getDsList(row)
  if (row) {
    const { name, ds_id, table_id, id, permission_list, ds_name, table_name } = row
    Object.assign(columnForm, {
      id,
      name,
      ds_id,
      ds_name,
      table_id,
      table_name,
      permissions: permission_list,
    })
  }
  dialogFormVisible.value = true
  dialogTitle.value = row?.id
    ? t('permission.edit_column_permission')
    : t('permission.add_column_permission')
}

const icon = (item: any) => {
  return (dsTypeWithImg.find((ele) => item.type === ele.type) || {}).img
}
let time: any
const handleInitDsIdChange = (val: any) => {
  columnForm.ds_id = val.id
  columnForm.ds_name = val.name
  time = setTimeout(() => {
    clearTimeout(time)
    columnFormRef.value.clearValidate('table_id')
  }, 0)
  datasourceApi.tableList(val.id).then((res: any) => {
    tableListOptions.value = res || []
    activeTable.value = null
    fieldListOptions.value = []
    columnForm.permissions = []
    if (authTreeRef.value) {
      authTreeRef.value.init({})
    }
  })
}

const handleDsIdChange = (val: any) => {
  columnForm.ds_id = val.id
  columnForm.ds_name = val.name
  datasourceApi.tableList(val.id).then((res: any) => {
    tableListOptions.value = res || []
    if (!columnForm.table_id) return
    tableListOptions.value.forEach((ele) => {
      if (+ele.id === +columnForm.table_id) {
        activeTable.value = ele
      }
    })
  })
}

const handleTableIdChange = (val: any) => {
  columnForm.table_id = val.id
  columnForm.table_name = val.table_name
  datasourceApi.fieldList(val.id).then((res: any) => {
    fieldListOptions.value = res || []
    if (columnForm.type === 'row') return
    columnForm.permissions = fieldListOptions.value.map((ele) => {
      const { id, field_name, field_comment } = ele
      return { field_id: id, field_name, field_comment, enable: true }
    })
  })
}

const handleEditeTable = (val: any) => {
  datasourceApi
    .fieldList(val)
    .then((res: any) => {
      fieldListOptions.value = res || []
      if (columnForm.type === 'row') return
      const enableMap = columnForm.permissions.reduce((pre, next) => {
        pre[next.field_id] = next.enable
        return pre
      }, {})
      columnForm.permissions = fieldListOptions.value.map((ele) => {
        const { id, field_name, field_comment } = ele
        return { field_id: id, field_name, field_comment, enable: enableMap[id] ?? false }
      })
    })
    .finally(() => {
      if (columnForm.type !== 'row') return
      authTreeRef.value.init(columnForm.expression_tree)
    })
}
const beforeClose = () => {
  if (termFormRef.value) {
    termFormRef.value.clearValidate()
  }
  ruleConfigvVisible.value = false
  activeStep.value = 0
  isCreate.value = false
}

const searchLoading = ref(false)
const handleSearch = () => {
  searchLoading.value = true
  getList()
    .then((res: any) => {
      ruleList.value = res || []
    })
    .finally(() => {
      searchLoading.value = false
    })
}
handleSearch()
const addHandler = () => {
  editRule.value = 0
  setDrawerTitle()
  isCreate.value = true
  Object.assign(currentPermission, cloneDeep(defaultPermission))
  ruleConfigvVisible.value = true
}

const editForm = (row: any) => {
  if (row.type === 'row') {
    ruleType.value = 1
    handleRowPermission(row)
  } else {
    ruleType.value = 0
    handleColumnPermission(row)
  }
}
const handleEditRule = (row: any) => {
  editRule.value = 1
  isCreate.value = false
  setDrawerTitle()
  Object.assign(currentPermission, cloneDeep(row))
  ruleConfigvVisible.value = true
}

const deleteRuleHandler = (row: any) => {
  ElMessageBox.confirm(t('permission.rule_rule_1', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    currentPermission.permissions = currentPermission.permissions.filter(
      (ele: any) => ele.id !== row.id
    )
  })
}

const deleteHandler = (row: any) => {
  ElMessageBox.confirm(t('permission.rule_group_1', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    delPermissions(row.id).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      handleSearch()
    })
  })
}
const setUser = (row: any) => {
  editRule.value = 2
  setDrawerTitle()
  isCreate.value = false
  Object.assign(currentPermission, cloneDeep(row))
  activeStep.value = 1
  ruleConfigvVisible.value = true
  nextTick(() => {
    selectPermissionRef.value.open(row.users)
  })
}

const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('permission.rule_group_name'),
      trigger: 'blur',
    },
  ],
}

const closeForm = () => {
  dialogFormVisible.value = false
}
const authTreeRef = ref()
const saveHandler = () => {
  columnFormRef.value.validate((res: any) => {
    const names = currentPermission.permissions
      .filter((ele: any) => ele.id !== columnForm.id)
      .map((ele: any) => ele.name)
    if (names.includes(columnForm.name)) {
      ElMessage.error(t('embedded.duplicate_name'))
      return
    }
    if (res) {
      if (columnForm.type === 'row') {
        authTreeRef.value.submit()
      } else {
        const { permissions, table_id, ds_id, type, name, ds_name, table_name } = columnForm
        if (columnForm.id) {
          for (const key in currentPermission.permissions) {
            if (currentPermission.permissions[key].id === columnForm.id) {
              Object.assign(
                currentPermission.permissions[key],
                cloneDeep({
                  permissions,
                  permission_list: permissions,
                  table_id,
                  ds_id,
                  type,
                  name,
                  ds_name,
                  table_name,
                })
              )
            }
          }
        } else {
          currentPermission.permissions.push(
            cloneDeep({
              permissions,
              permission_list: permissions,
              table_id,
              ds_id,
              type,
              name,
              ds_name,
              table_name,
              id: +new Date(),
            })
          )
        }
        dialogFormVisible.value = false
      }
    }
  })
}
const preview = () => {
  currentPermission.user = selectPermissionRef.value.checkTableList.map((ele: any) => ele.id)
  activeStep.value = 0
}
const next = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      activeStep.value = 1
      nextTick(() => {
        selectPermissionRef.value.open(currentPermission.users)
      })
    }
  })
}
const saveLoading = ref(false)
const save = () => {
  const { id, name, permissions, users } = cloneDeep(currentPermission)

  const permissionsObj = permissions.map((ele: any) => {
    return {
      ...cloneDeep(ele),
      permissions:
        ele.type !== 'row'
          ? typeof ele.permissions === 'object'
            ? JSON.stringify(ele.permissions || [])
            : ele.permissions
          : JSON.stringify([]),
      permission_list: [],
      expression_tree:
        ele.type === 'row'
          ? typeof ele.expression_tree === 'object'
            ? JSON.stringify(ele.expression_tree || {})
            : ele.expression_tree
          : JSON.stringify({}),
    }
  })
  const obj = {
    id,
    name,
    permissions: permissionsObj,
    users:
      isCreate.value || activeStep.value === 1
        ? selectPermissionRef.value.checkTableList.map((ele: any) => ele.id)
        : users,
  }
  if (!id) {
    delete obj.id
  }
  if (saveLoading.value) return
  saveLoading.value = true
  savePermissions(obj)
    .then(() => {
      ElMessage({
        type: 'success',
        message: t('common.save_success'),
      })
      beforeClose()
      handleSearch()
    })
    .finally(() => {
      saveLoading.value = false
    })
}
const savePermission = () => {
  if (!isCreate.value && activeStep.value === 0) {
    termFormRef.value.validate((res: any) => {
      if (res) {
        save()
      }
    })
    return
  }

  save()
}

const columnRules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('permission.rule_name'),
      trigger: 'blur',
    },
  ],
  table_id: [
    {
      required: true,
      message: t('datasource.Please_select') + t('common.empty') + t('permission.data_table'),
      trigger: 'change',
    },
  ],
}
</script>

<template>
  <div v-loading="searchLoading" class="permission no-padding">
    <div class="tool-left">
      <span class="page-title">{{ $t('workspace.permission_configuration') }}</span>
      <div>
        <el-input
          v-model="keywords"
          clearable
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('permission.search_rule_group')"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="addHandler()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('permission.add_rule_group') }}
        </el-button>
      </div>
    </div>

    <EmptyBackground
      v-if="!!keywords && !ruleListWithSearch.length"
      :description="$t('datasource.relevant_content_found')"
      img-type="tree"
    />

    <div v-else class="card-content">
      <el-row :gutter="16" class="w-full">
        <el-col
          v-for="ele in ruleListWithSearch"
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
            :type="ele.users.length"
            :num="ele.permissions.length"
            @edit="handleEditRule(ele)"
            @del="deleteHandler(ele)"
            @set-user="setUser(ele)"
          ></Card>
        </el-col>
      </el-row>
    </div>
    <template v-if="!keywords && !ruleListWithSearch.length && !searchLoading">
      <EmptyBackground
        class="ed-empty_200"
        :description="$t('permission.no_permission_rule')"
        img-type="noneWhite"
      />

      <div style="text-align: center; margin-top: -10px">
        <el-button type="primary" @click="addHandler()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('permission.add_rule_group') }}
        </el-button>
      </div>
    </template>
    <el-drawer
      v-model="ruleConfigvVisible"
      :close-on-click-modal="false"
      size="calc(100% - 100px)"
      modal-class="permission-drawer-fullscreen"
      direction="btt"
      :before-close="beforeClose"
      :show-close="false"
    >
      <template #header="{ close }">
        <span style="white-space: nowrap">{{ drawerTitle }}</span>
        <div v-if="isCreate" class="flex-center" style="width: 100%">
          <el-steps custom style="max-width: 500px; flex: 1" :active="activeStep" align-center>
            <el-step>
              <template #title> {{ $t('permission.set_permission_rule') }} </template>
            </el-step>
            <el-step>
              <template #title> {{ $t('permission.select_restricted_user') }} </template>
            </el-step>
          </el-steps>
        </div>
        <el-icon class="ed-dialog__headerbtn mrt" style="cursor: pointer" @click="close">
          <icon_close_outlined></icon_close_outlined>
        </el-icon>
      </template>

      <div v-show="activeStep === 0" class="drawer-content">
        <el-scrollbar>
          <div class="scroll-content">
            <div class="title">
              {{ $t('ds.form.base_info') }}
            </div>

            <el-form
              ref="termFormRef"
              :model="currentPermission"
              label-width="180px"
              label-position="top"
              :rules="rules"
              class="form-content_error"
              @submit.prevent
            >
              <el-form-item prop="name" :label="t('permission.rule_group_name')">
                <el-input
                  v-model="currentPermission.name"
                  maxlength="50"
                  clearable
                  :placeholder="
                    $t('datasource.please_enter') +
                    $t('common.empty') +
                    $t('permission.rule_group_name')
                  "
                  autocomplete="off"
                />
              </el-form-item>

              <el-form-item class="add-permission_form">
                <template #label>
                  <div
                    style="
                      width: 100%;
                      display: flex;
                      align-items: center;
                      justify-content: space-between;
                      font-size: 16px;
                      font-weight: 500;
                    "
                  >
                    {{ t('permission.permission_rule') }}

                    <el-popover popper-class="system-permission_user" placement="bottom">
                      <template #reference>
                        <el-button class="add-btn" type="primary">
                          {{ $t('model.add') }}
                          <el-icon style="margin-left: 4px" size="16">
                            <icon_down_outlined></icon_down_outlined>
                          </el-icon>
                        </el-button>
                      </template>
                      <div class="popover">
                        <div class="popover-content">
                          <div
                            v-for="ele in userTypeList"
                            :key="ele.name"
                            class="popover-item"
                            @click="handleAddPermission(ele.value)"
                          >
                            <div class="model-name">{{ ele.name }}</div>
                          </div>
                        </div>
                      </div>
                    </el-popover>
                  </div>
                </template>
                <div
                  class="table-content"
                  :class="!currentPermission.permissions.length && 'border-bottom'"
                >
                  <el-table
                    :empty-text="$t('permission.no_rule')"
                    :data="currentPermission.permissions"
                    style="width: 100%"
                  >
                    <el-table-column prop="name" :label="$t('permission.rule_name')" />
                    <el-table-column prop="type" :label="$t('permission.type')">
                      <template #default="scope">
                        {{
                          scope.row.type === 'row'
                            ? $t('permission.row_permission')
                            : $t('permission.column_permission')
                        }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="ds_name" :label="$t('permission.data_source')" />
                    <el-table-column prop="table_name" :label="$t('permission.data_table')" />
                    <el-table-column
                      class-name="actions-methods"
                      fixed="right"
                      width="80"
                      :label="$t('ds.actions')"
                    >
                      <template #default="scope">
                        <el-tooltip
                          :offset="14"
                          effect="dark"
                          :content="$t('datasource.edit')"
                          placement="top"
                        >
                          <el-icon class="action-btn" size="16" @click="editForm(scope.row)">
                            <IconOpeEdit></IconOpeEdit>
                          </el-icon>
                        </el-tooltip>

                        <el-tooltip
                          :offset="14"
                          effect="dark"
                          :content="$t('dashboard.delete')"
                          placement="top"
                        >
                          <el-icon
                            class="action-btn"
                            size="16"
                            @click="deleteRuleHandler(scope.row)"
                          >
                            <IconOpeDelete></IconOpeDelete>
                          </el-icon>
                        </el-tooltip>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-form-item>
            </el-form>
          </div>
        </el-scrollbar>
      </div>
      <div v-show="activeStep !== 0" class="select-permission_content">
        <el-scrollbar>
          <div class="scroll-content">
            <SelectPermission ref="selectPermissionRef"></SelectPermission>
          </div>
        </el-scrollbar>
      </div>
      <template #footer>
        <el-button secondary @click="beforeClose"> {{ $t('common.cancel') }} </el-button>
        <el-button v-if="activeStep === 1 && isCreate" secondary @click="preview">
          {{ t('ds.previous') }}
        </el-button>
        <el-button v-if="activeStep === 0 && isCreate" type="primary" @click="next">
          {{ t('common.next') }}
        </el-button>
        <el-button
          v-if="(isCreate && activeStep === 1) || !isCreate"
          type="primary"
          @click="savePermission"
        >
          {{ $t('common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <el-drawer
      v-model="dialogFormVisible"
      :title="dialogTitle"
      destroy-on-close
      size="896px"
      modal-class="column-form_drawer"
      :before-close="closeForm"
    >
      <el-form
        ref="columnFormRef"
        :model="columnForm"
        label-width="180px"
        label-position="top"
        :rules="columnRules"
        class="form-content_error"
        @submit.prevent
      >
        <el-form-item prop="name" :label="t('permission.rule_name')">
          <el-input
            v-model="columnForm.name"
            maxlength="50"
            clearable
            :placeholder="
              $t('datasource.please_enter') + $t('common.empty') + $t('permission.rule_name')
            "
            autocomplete="off"
          />
        </el-form-item>
        <el-form-item prop="table_id" :label="t('permission.data_table')">
          <el-select
            v-model="activeDs"
            filterable
            style="width: 416px"
            value-key="id"
            :placeholder="
              $t('datasource.Please_select') + $t('common.empty') + $t('permission.data_source')
            "
            @change="handleInitDsIdChange"
          >
            <el-option
              v-for="item in dsListOptions"
              :key="item.id"
              :label="item.name"
              :value="item"
            >
              <div style="display: flex; align-items: center">
                <img :src="icon(item)" width="24" height="24" style="margin-right: 8px" />
                {{ item.name }}
              </div>
            </el-option>
          </el-select>
          <el-select
            v-model="activeTable"
            filterable
            style="width: 416px; margin-left: auto"
            :disabled="!columnForm.ds_id"
            value-key="id"
            :placeholder="
              $t('datasource.Please_select') + $t('common.empty') + $t('permission.data_table')
            "
            @change="handleTableIdChange"
          >
            <el-option
              v-for="item in tableListOptions"
              :key="item.id"
              :label="item.table_name"
              :value="item"
            >
              <div style="display: flex; align-items: center">
                <el-icon size="16" style="margin-right: 8px; color: #646a73">
                  <ICON_TABLE />
                </el-icon>
                {{ item.table_name }}
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('permission.set_rule')">
          <el-input
            v-if="ruleType !== 1"
            v-model="searchColumn"
            :placeholder="$t('permission.search_rule_group')"
            autocomplete="off"
            clearable
            ><template #prefix>
              <el-icon>
                <icon_searchOutline_outlined />
              </el-icon> </template
          ></el-input>
        </el-form-item>
      </el-form>
      <div v-if="ruleType === 1" class="auth-tree_content">
        <AuthTree ref="authTreeRef" @save="saveAuthTree"></AuthTree>
      </div>
      <div v-else class="table-content">
        <el-table
          :empty-text="$t('permission.no_fields_yet')"
          :data="tableColumnData"
          style="width: 100%"
        >
          <el-table-column prop="field_name" :label="$t('datasource.field_name')" />
          <el-table-column prop="field_comment" :label="$t('datasource.field_notes')" />
          <el-table-column fixed="right" width="150" :label="$t('ds.actions')">
            <template #default="scope">
              <el-switch v-model="scope.row.enable" size="small" />
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button secondary @click="closeForm">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="saveHandler">
            {{ $t('common.save') }}
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="less" scoped>
.permission {
  height: 100%;
  width: 100%;
  padding: 16px 0 16px 0;

  .ed-empty_200 {
    padding-top: 292px;
    padding-bottom: 0;
    height: auto;
  }
  .tool-left {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding: 0 24px 0 24px;

    .page-title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }
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
}
</style>

<style lang="less">
.permission-drawer-fullscreen {
  .ed-drawer__body {
    padding-left: 0;
    padding-right: 0;
  }
  .title {
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
    margin-top: 8px;
    margin-bottom: 16px;
  }

  .select-permission_content,
  .drawer-content {
    width: 100%;
    height: 100%;
    padding-bottom: 24px;
    & > .ed-scrollbar {
      .scroll-content {
        width: 800px;
        margin: 0 auto;
      }
    }
  }

  .drawer-content {
    .add-btn:hover {
      .ed-icon {
        transform: rotate(180deg);
      }
    }
    .add-permission_form {
      margin-bottom: 0;
      .ed-form-item__label {
        width: 100%;
        padding-right: 0;
      }

      .ed-form-item__content {
        padding-bottom: 0px;
      }

      .table-content {
        width: 100%;
        margin-top: 16px;
        border: 1px solid #1f232926;
        border-top: none;
        border-bottom: none;
        border-radius: 6px;
        overflow-y: auto;

        &.border-bottom {
          border-bottom: 1px solid #1f232926;
        }
        .ed-table__empty-text {
          padding-top: 0;
        }

        .actions-methods {
          .cell {
            height: 24px;
            .action-btn {
              margin-top: 4px;
              &:nth-child(1) {
                margin-right: 12px;
              }
            }
          }
        }

        .ed-icon {
          position: relative;
          cursor: pointer;
          color: #646a73;

          &::after {
            content: '';
            background-color: #1f23291a;
            position: absolute;
            border-radius: 6px;
            width: 24px;
            height: 24px;
            transform: translate(-50%, -50%);
            top: 50%;
            left: 50%;
            display: none;
          }

          &:hover {
            &::after {
              display: block;
            }
          }
        }
      }
    }
  }
}

.column-form_drawer {
  .table-content {
    width: 100%;
    margin-top: 16px;
    border: 1px solid #1f232926;
    border-top: none;
    border-radius: 6px;
    overflow-y: auto;
    max-height: calc(100vh - 400px);
    .ed-table__empty-text {
      padding-top: 0;
    }
  }

  .auth-tree_content {
    padding: 16px;
    border-radius: 6px;
    border: 1px solid #dee0e3;
    min-height: 64px;
    display: flex;
    align-items: center;
    overflow-y: auto;
    margin-top: -16px;
  }
}

.system-permission_user.system-permission_user {
  padding: 0;
  width: 120px !important;
  min-width: 120px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .popover {
    .popover-content {
      padding: 4px;
      position: relative;
      &::after {
        position: absolute;
        content: '';
        left: 0;
        top: 40px;
        width: 100%;
        height: 1px;
        background: #1f232926;
      }
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      &:hover {
        background: #1f23291a;
      }

      &:nth-child(2) {
        margin: 9px 0 0 0;
      }

      .model-name {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}
</style>
