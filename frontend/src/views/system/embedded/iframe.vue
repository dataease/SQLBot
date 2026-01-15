<script lang="ts" setup>
import { ref, computed, reactive, nextTick } from 'vue'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import icon_database_colorful from '@/assets/embedded/icon_database_colorful.png'
import icon_web_site_colorful from '@/assets/embedded/icon_web-site_colorful.png'
import floating_window from '@/assets/embedded/window.png'
import full_window from '@/assets/embedded/Card.png'
import icon_edit_outlined from '@/assets/svg/icon_edit_outlined.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import icon_copy_outlined from '@/assets/embedded/icon_copy_outlined.svg'
import { useClipboard } from '@vueuse/core'
import SetUi from './SetUi.vue'
import Card from './Card.vue'
// import { workspaceList } from '@/api/workspace'
import DsCard from './DsCard.vue'
import { getList, updateAssistant, saveAssistant, delOne, dsApi } from '@/api/embedded'
import { useI18n } from 'vue-i18n'
import { cloneDeep } from 'lodash-es'
import { useUserStore } from '@/stores/user.ts'

const userStore = useUserStore()
defineProps({
  btnSelect: {
    type: String,
    default: '',
  },
})

// const emits = defineEmits(['btnSelectChange'])

const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })

const keywords = ref('')
const activeStep = ref(0)
const ruleConfigvVisible = ref(false)
const drawerConfigvVisible = ref(false)
const advancedApplication = ref(false)
const editRule = ref(0)
const embeddedFormRef = ref()
const dsFormRef = ref()
const urlFormRef = ref()
const certificateFormRef = ref()
const dialogTitle = ref('')
const drawerTitle = ref('')
const activeMode = ref('full')

const embeddedList = ref<any[]>([])
const systemCredentials = ['localStorage', 'custom', 'cookie', 'sessionStorage']
const credentials = ['header', 'cookie', 'param']

const defaultEmbedded = {
  id: '',
  name: '',
  type: 0,
  description: '',
  configuration: '',
  domain: '',
}
const currentEmbedded = reactive<any>(cloneDeep(defaultEmbedded))

const isCreate = ref(false)
const defaultForm = {
  oid: 1,
  public_list: [],
  private_list: [],
  auto_ds: false,
}

const dsForm = reactive<{ [key: string]: any }>(cloneDeep(defaultForm))

const defaultCertificateForm = {
  id: '',
  type: '',
  source: '',
  target: '',
  target_key: '',
  target_val: '',
}
const certificateForm = reactive(cloneDeep(defaultCertificateForm))

const defaultUrlForm = {
  endpoint: '',
  timeout: 10,
  encrypt: false,
  aes_key: '',
  aes_iv: '',
  certificate: [] as any,
  auto_ds: false,
}
const urlForm = reactive(cloneDeep(defaultUrlForm))

const dsListOptions = ref<any[]>([])

const embeddedListWithSearch = computed(() => {
  if (!keywords.value) return embeddedList.value
  return embeddedList.value.filter((ele: any) =>
    ele.name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})

const userTypeList = [
  {
    name: t('embedded.basic_application'),
    img: icon_database_colorful,
    tip: t('embedded.support_is_required'),
    value: 0,
  },
  {
    name: t('embedded.advanced_application'),
    img: icon_web_site_colorful,
    tip: t('embedded.data_permissions_etc'),
    value: 1,
  },
]

const handleAddEmbedded = (val: any) => {
  Object.assign(currentEmbedded, cloneDeep(defaultEmbedded))
  Object.keys(dsForm).forEach((ele) => {
    if (!['oid', 'public_list', 'private_list'].includes(ele)) {
      delete dsForm[ele]
    }
  })
  Object.assign(urlForm, cloneDeep(defaultUrlForm))
  currentEmbedded.type = val
  if (val === 0) {
    handleBaseEmbedded(null)
  } else {
    handleAdvancedEmbedded(null)
  }
}

const getDsList = () => {
  dsApi(dsForm.oid).then((res: any) => {
    dsListOptions.value = res || []
  })
}
const handleBaseEmbedded = (row: any) => {
  advancedApplication.value = false
  if (row) {
    Object.assign(dsForm, JSON.parse(row.configuration))
  } else {
    Object.assign(dsForm, { oid: userStore.getOid })
  }
  getDsList()
  ruleConfigvVisible.value = true
  dialogTitle.value = row?.id
    ? t('embedded.edit_basic_applications')
    : t('embedded.create_basic_application')
}
const handleAdvancedEmbedded = (row: any) => {
  advancedApplication.value = true
  if (row) {
    const tempData = cloneDeep(JSON.parse(row.configuration))
    if (tempData?.endpoint.startsWith('http')) {
      row.domain
        .trim()
        .split(',')
        .forEach((domain: string) => {
          tempData.endpoint = tempData.endpoint.replace(domain, '')
        })
    }
    Object.assign(urlForm, tempData)
  }
  ruleConfigvVisible.value = true
  dialogTitle.value = row?.id
    ? t('embedded.edit_advanced_applications')
    : t('embedded.creating_advanced_applications')
}

const beforeClose = () => {
  ruleConfigvVisible.value = false
  activeStep.value = 0
  isCreate.value = false
  Object.assign(currentEmbedded, cloneDeep(defaultEmbedded))
  Object.assign(dsForm, cloneDeep(defaultForm))
  Object.assign(urlForm, cloneDeep(defaultUrlForm))

  if (embeddedFormRef.value) {
    embeddedFormRef.value.clearValidate()
  }

  if (dsFormRef.value) {
    dsFormRef.value.clearValidate()
  }

  if (urlFormRef.value) {
    urlFormRef.value.clearValidate()
  }
}

const handleActive = (row: any) => {
  console.info('row', row)
}

const handlePrivate = (row: any) => {
  dsForm.public_list = dsForm.public_list.filter((ele: any) => ele !== row.id)
}

const handlePublic = (row: any) => {
  dsForm.public_list.push(row.id)
}

const searchLoading = ref(false)
const handleSearch = () => {
  searchLoading.value = true
  getList()
    .then((res: any) => {
      embeddedList.value = res || []
    })
    .finally(() => {
      searchLoading.value = false
    })
}
handleSearch()

const handleEditRule = (row: any) => {
  Object.assign(currentEmbedded, cloneDeep(row))
  delete currentEmbedded.configuration
  if (row.type === 0) {
    handleBaseEmbedded(row)
  } else {
    handleAdvancedEmbedded(row)
  }
}

// const deleteRuleHandler = (row: any) => {
//   ElMessageBox.confirm(t('permission.rule_rule_1', { msg: row.name }), {
//     confirmButtonType: 'danger',
//     confirmButtonText: t('dashboard.delete'),
//     cancelButtonText: t('common.cancel'),
//     customClass: 'confirm-no_icon',
//     autofocus: false,
//   }).then(() => {
//     currentEmbedded.permissions = currentEmbedded.permissions.filter(
//       (ele: any) => ele.id !== row.id
//     )
//   })
// }

const deleteHandler = (row: any) => {
  ElMessageBox.confirm(t('embedded.delete', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    delOne(row.id).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      handleSearch()
    })
  })
}
const setUiRef = ref()
const handleSetUi = (row: any) => {
  setUiRef.value.open(row)
}
const splitString = (str: string) => {
  if (typeof str !== 'string') {
    return []
  }
  return str
    .split(/[,;]/)
    .map((item) => item.trim())
    .filter((item) => item !== '')
}
const validateUrl = (_: any, value: any, callback: any) => {
  if (value === '') {
    callback(
      new Error(
        t('datasource.please_enter') + t('common.empty') + t('embedded.cross_domain_settings')
      )
    )
  } else {
    // var Expression = /(https?:\/\/)?([\da-z\.-]+)\.([a-z]{2,6})(:\d{1,5})?([\/\w\.-]*)*\/?(#[\S]+)?/ // eslint-disable-line
    splitString(value).forEach((tempVal: string) => {
      var Expression = /^https?:\/\/[^\s/?#]+(:\d+)?/i
      var objExp = new RegExp(Expression)
      if (objExp.test(tempVal) && !tempVal.endsWith('/')) {
        callback()
      } else {
        callback(t('embedded.format_is_incorrect', { msg: t('embedded.domain_format_incorrect') }))
      }
    })
  }
}
const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('embedded.application_name'),
      trigger: 'blur',
    },
  ],
  domain: [
    {
      required: true,
      validator: validateUrl,
      trigger: 'blur',
    },
  ],
}

const dsRules = {
  oid: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.workspace'),
      trigger: 'change',
    },
  ],
}
const validatePass = (_: any, value: any, callback: any) => {
  if (value === '') {
    callback(
      new Error(t('datasource.please_enter') + t('common.empty') + t('embedded.interface_url'))
    )
  } else {
    // var Expression = /(https?:\/\/)?([\da-z\.-]+)\.([a-z]{2,6})(:\d{1,5})?([\/\w\.-]*)*\/?(#[\S]+)?/ // eslint-disable-line
    // var Expression = /^https?:\/\/[^\s/?#]+(:\d+)?/i
    var Expression = /^\/([a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+(\?[a-zA-Z0-9_=&-]+)?$/
    var objExp = new RegExp(Expression)
    if (objExp.test(value)) {
      callback()
    } else {
      callback(t('embedded.format_is_incorrect', { msg: t('embedded.interface_url_incorrect') }))
    }
  }
}

const validateCertificate = (_: any, value: any, callback: any) => {
  if (!value.length) {
    callback(new Error(t('menu.add_interface_credentials')))
  } else {
    callback()
  }
}

const validateTimeout = (_: any, value: any, callback: any) => {
  if (value === null) {
    callback(new Error(t('datasource.please_enter') + t('common.empty') + t('ds.form.timeout')))
  } else {
    callback()
  }
}

const urlRules = {
  endpoint: [
    {
      required: true,
      validator: validatePass,
      trigger: 'blur',
    },
  ],
  timeout: [
    {
      required: true,
      validator: validateTimeout,
      trigger: 'change',
    },
  ],
  certificate: [
    {
      required: true,
      validator: validateCertificate,
      trigger: 'change',
    },
  ],
}

const certificateRules = {
  type: [
    {
      required: true,
      message:
        t('datasource.Please_select') + t('common.empty') + t('embedded.system_credential_type'),
      trigger: 'change',
    },
  ],
  source: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('embedded.credential_name'),
      trigger: 'blur',
    },
  ],

  target: [
    {
      required: true,
      message:
        t('datasource.Please_select') +
        t('common.empty') +
        t('embedded.target_credential_location'),
      trigger: 'change',
    },
  ],
  target_key: [
    {
      required: true,
      message:
        t('datasource.please_enter') + t('common.empty') + t('embedded.target_credential_name'),
      trigger: 'blur',
    },
  ],
}

const preview = () => {
  activeStep.value = 0
}
const next = () => {
  embeddedFormRef.value.validate((res: any) => {
    if (res) {
      activeStep.value = 1
    }
  })
}
const saveEmbedded = () => {
  const req = currentEmbedded.id ? updateAssistant : saveAssistant
  const formRef = currentEmbedded.type === 1 ? urlFormRef : dsFormRef
  formRef.value.validate((res: any) => {
    if (res) {
      const obj = { ...currentEmbedded }
      if (currentEmbedded.type === 0) {
        obj.configuration = JSON.stringify(dsForm)
      } else {
        obj.configuration = JSON.stringify(urlForm)
      }

      if (!currentEmbedded.id) {
        delete obj.id
      }
      req(obj).then(() => {
        ElMessage({
          type: 'success',
          message: t('common.save_success'),
        })
        beforeClose()
        handleSearch()
      })
    }
  })
}

const dialogVisible = ref(false)
const scriptElement = ref('')
const jsCodeElement = ref('')
const jsCodeElementFull = ref('')
const handleEmbedded = (row: any) => {
  dialogVisible.value = true
  const { origin, pathname } = window.location
  scriptElement.value = `g-#script
  async
  defer
  id="sqlbot-assistant-float-script-${row.id}"
  src="${origin + pathname}assistant.js?id=${row.id}"k-*g-#/scriptk-*`
    .replaceAll('g-#', '<')
    .replaceAll('k-*', '>')

  jsCodeElement.value = `(function(){
    const script = document.createElement('script');
    script.defer = true;
    script.async = true;
    script.src = "${origin + pathname}assistant.js?id=${row.id}";
    script.id = "sqlbot-assistant-float-script-${row.id}";
    document.head.appendChild(script);
  })()`

  jsCodeElementFull.value = `(function(){
    const script = document.createElement('script');
    script.defer = true;
    script.async = true;
    script.src = "${origin + pathname}xpack_static/sqlbot-embedded-dynamic.umd.js";
    document.head.appendChild(script);
  })()
  let sqlbot_embedded_timer = setInterval(() => {
    if (sqlbot_embedded_handler?.mounted) {
      sqlbot_embedded_handler.mounted('.copilot', { "embeddedId": "${row.id}" })
      clearInterval(sqlbot_embedded_timer)
    }
  }, 1000)
  `
}
const copyJsCode = () => {
  copy(jsCodeElement.value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}

const copyJsCodeFull = () => {
  copy(jsCodeElementFull.value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
const copyCode = () => {
  copy(scriptElement.value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
const certificateBeforeClose = () => {
  drawerConfigvVisible.value = false
  Object.assign(certificateForm, cloneDeep(defaultCertificateForm))
  certificateFormRef.value.clearValidate()
}

const initCertificate = (row: any) => {
  drawerTitle.value = t('embedded.add_interface_credentials')
  if (row) {
    Object.assign(certificateForm, cloneDeep(row))
    drawerTitle.value = t('embedded.edit_interface_credentials')
  } else {
    Object.assign(certificateForm, cloneDeep(defaultCertificateForm))
  }
  drawerConfigvVisible.value = true
  nextTick(() => {
    certificateFormRef.value.clearValidate()
  })
}

const handleCredentialsDel = (row: any) => {
  urlForm.certificate = urlForm.certificate.filter((ele: any) => ele.id !== row.id)
}

const saveHandler = () => {
  certificateFormRef.value.validate((res: any) => {
    if (res) {
      if (certificateForm.id) {
        for (const key in urlForm.certificate) {
          if (Object.prototype.hasOwnProperty.call(urlForm.certificate, key)) {
            if (urlForm.certificate[key].id === certificateForm.id) {
              Object.assign(urlForm.certificate[key], cloneDeep(certificateForm))
            }
          }
        }
      } else {
        urlForm.certificate.push({ ...cloneDeep(certificateForm), id: +new Date() })
      }

      ElMessage({
        type: 'success',
        message: t('common.save_success'),
      })
      urlFormRef.value.validate('certificate')
      certificateBeforeClose()
    }
  })
}
</script>

<template>
  <div v-loading="searchLoading" class="embedded-index no-padding">
    <div class="tool-left">
      <span class="page-title">{{ t('embedded.assistant_app') }}</span>
      <!-- <div class="btn-select">
        <el-button
          :class="[btnSelect === 'd' && 'is-active']"
          text
          @click="emits('btnSelectChange', 'd')"
        >
          {{ t('embedded.embedded_assistant') }}
        </el-button>
        <el-button
          :class="[btnSelect === 'q' && 'is-active']"
          text
          @click="emits('btnSelectChange', 'q')"
        >
          {{ t('embedded.embedded_page') }}
        </el-button>
      </div> -->
      <div>
        <el-input
          v-model="keywords"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('dashboard.search')"
          clearable
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>

        <el-popover popper-class="system-embedded_user" placement="bottom-end">
          <template #reference>
            <el-button type="primary">
              <template #icon>
                <icon_add_outlined></icon_add_outlined>
              </template>
              {{ $t('embedded.create_application') }}
            </el-button>
          </template>
          <div class="popover">
            <div class="popover-content">
              <div
                v-for="ele in userTypeList"
                :key="ele.name"
                class="popover-item"
                @click="handleAddEmbedded(ele.value)"
              >
                <img :src="ele.img" style="margin-top: 5px" width="32px" height="32px" />
                <div class="embedded">
                  <div class="name">{{ ele.name }}</div>
                  <div class="tip">{{ ele.tip }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <EmptyBackground
      v-if="!!keywords && !embeddedListWithSearch.length"
      :description="$t('datasource.relevant_content_found')"
      img-type="tree"
      class="ed-empty_pd0"
    />
    <div v-else class="card-content">
      <el-row :gutter="16" class="w-full">
        <el-col
          v-for="ele in embeddedListWithSearch"
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
            :is-base="ele.type === 0"
            :description="ele.description"
            :logo="JSON.parse(ele.configuration).logo"
            @embedded="handleEmbedded(ele)"
            @edit="handleEditRule(ele)"
            @del="deleteHandler(ele)"
            @ui="handleSetUi(ele)"
          ></Card>
        </el-col>
      </el-row>
    </div>
    <template v-if="!keywords && !embeddedListWithSearch.length && !searchLoading">
      <EmptyBackground
        class="ed-empty_custom"
        :description="$t('embedded.no_application')"
        img-type="noneWhite"
      />

      <div style="text-align: center; margin-top: -10px">
        <el-popover popper-class="system-embedded_user" placement="bottom">
          <template #reference>
            <el-button type="primary">
              <template #icon>
                <icon_add_outlined></icon_add_outlined>
              </template>
              {{ $t('embedded.create_application') }}
            </el-button>
          </template>
          <div class="popover">
            <div class="popover-content">
              <div
                v-for="ele in userTypeList"
                :key="ele.name"
                class="popover-item"
                @click="handleAddEmbedded(ele.value)"
              >
                <img :src="ele.img" style="margin-top: 5px" width="32px" height="32px" />
                <div class="embedded">
                  <div class="name">{{ ele.name }}</div>
                  <div class="tip">{{ ele.tip }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
    </template>
    <el-drawer
      v-model="ruleConfigvVisible"
      :close-on-click-modal="false"
      size="calc(100% - 100px)"
      modal-class="embedded-drawer-fullscreen"
      direction="btt"
      :before-close="beforeClose"
      :show-close="false"
    >
      <template #header="{ close }">
        <span style="white-space: nowrap">{{ dialogTitle }}</span>
        <div v-if="editRule !== 2" class="flex-center" style="width: 100%">
          <el-steps custom style="max-width: 500px; flex: 1" :active="activeStep" align-center>
            <el-step>
              <template #title> {{ $t('embedded.basic_information') }} </template>
            </el-step>
            <el-step>
              <template #title>
                {{
                  currentEmbedded.type === 1
                    ? $t('embedded.configure_interface')
                    : $t('embedded.set_data_source')
                }}
              </template>
            </el-step>
          </el-steps>
        </div>
        <el-icon style="cursor: pointer" @click="close">
          <icon_close_outlined></icon_close_outlined>
        </el-icon>
      </template>

      <div v-if="activeStep === 0" class="drawer-content">
        <el-scrollbar>
          <div class="scroll-content">
            <div class="title">
              {{ $t('embedded.basic_information') }}
            </div>

            <el-form
              ref="embeddedFormRef"
              :model="currentEmbedded"
              label-width="180px"
              label-position="top"
              :rules="rules"
              class="form-content_error"
              @submit.prevent
            >
              <el-form-item prop="name" :label="t('embedded.application_name')">
                <el-input
                  v-model="currentEmbedded.name"
                  :placeholder="
                    $t('datasource.please_enter') +
                    $t('common.empty') +
                    $t('embedded.application_name')
                  "
                  clearable
                  maxlength="50"
                  autocomplete="off"
                />
              </el-form-item>

              <el-form-item prop="description" :label="t('embedded.application_description')">
                <el-input
                  v-model="currentEmbedded.description"
                  :rows="3"
                  type="textarea"
                  maxlength="200"
                  show-word-limit
                  clearable
                  :placeholder="$t('datasource.please_enter')"
                  autocomplete="off"
                />
              </el-form-item>

              <el-form-item prop="domain" :label="t('embedded.cross_domain_settings')">
                <el-input
                  v-model="currentEmbedded.domain"
                  type="textarea"
                  :autosize="{ minRows: 2 }"
                  clearable
                  :placeholder="$t('embedded.third_party_address')"
                  autocomplete="off"
                />
              </el-form-item>
            </el-form>
          </div>
        </el-scrollbar>
      </div>
      <div v-if="activeStep === 1 && advancedApplication" class="drawer-content">
        <el-scrollbar>
          <div class="scroll-content">
            <div class="title">
              {{ $t('embedded.configure_interface') }}
            </div>

            <el-form
              ref="urlFormRef"
              :model="urlForm"
              label-width="180px"
              label-position="top"
              :rules="urlRules"
              class="form-content_error"
              @submit.prevent
            >
              <el-form-item prop="endpoint" :label="t('embedded.interface_url')">
                <el-input
                  v-model="urlForm.endpoint"
                  clearable
                  :placeholder="
                    $t('datasource.please_enter') +
                    $t('common.empty') +
                    $t('embedded.interface_url')
                  "
                  autocomplete="off"
                />
              </el-form-item>
              <el-form-item :label="t('ds.form.timeout')" prop="timeout">
                <el-input-number
                  v-model="urlForm.timeout"
                  clearable
                  :min="0"
                  :max="300"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item prop="AES" class="custom-require">
                <template #label>
                  <span class="custom-require_danger">{{ t('embedded.aes_enable') }}</span>
                </template>

                <el-switch v-model="urlForm.encrypt" />
                <span class="aes-encrypt-tips">{{ t('embedded.aes_enable_tips') }}</span>
              </el-form-item>
              <el-form-item v-if="urlForm.encrypt" prop="aes_key" label="AES Key">
                <el-input
                  v-model="urlForm.aes_key"
                  clearable
                  type="password"
                  show-password
                  :placeholder="
                    $t('datasource.please_enter') +
                    $t('common.empty') +
                    ' 32 ' +
                    $t('embedded.bit') +
                    ' AES Key'
                  "
                  autocomplete="off"
                />
              </el-form-item>

              <el-form-item class="certificate-table_form" prop="certificate">
                <template #label>
                  <div class="title-content">
                    <span class="title-form">{{ t('embedded.interface_credentials') }}</span>
                    <span class="add btn" @click="initCertificate(null)">
                      <el-icon size="16">
                        <icon_add_outlined></icon_add_outlined>
                      </el-icon>
                      {{ t('model.add') }}
                    </span>
                  </div>
                </template>
                <div
                  class="table-content"
                  :class="!!urlForm.certificate.length && 'no-credentials_yet'"
                >
                  <el-table
                    :empty-text="$t('embedded.no_credentials_yet')"
                    :data="urlForm.certificate"
                    style="width: 100%"
                  >
                    <el-table-column
                      prop="source"
                      :label="t('embedded.credential_name')"
                      width="180"
                    />
                    <el-table-column
                      prop="type"
                      :label="t('embedded.system_credential_type')"
                      width="180"
                    />
                    <el-table-column
                      prop="target_key"
                      :label="t('embedded.target_credential_name')"
                      width="180"
                    />
                    <el-table-column
                      prop="target"
                      :label="t('embedded.target_credential_location')"
                    />
                    <el-table-column
                      fixed="right"
                      width="80"
                      class-name="operation-column_text"
                      :label="$t('ds.actions')"
                    >
                      <template #default="scope">
                        <el-button text type="primary" @click="initCertificate(scope.row)">
                          <el-icon size="16">
                            <icon_edit_outlined></icon_edit_outlined>
                          </el-icon>
                        </el-button>
                        <el-button text type="primary" @click="handleCredentialsDel(scope.row)">
                          <el-icon size="16">
                            <icon_delete></icon_delete>
                          </el-icon>
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-form-item>

              <el-form-item prop="auto_ds" :label="t('embedded.auto_select_ds')">
                <el-switch v-model="urlForm.auto_ds" />
              </el-form-item>
            </el-form>
          </div>
        </el-scrollbar>
      </div>
      <div v-if="activeStep === 1 && !advancedApplication" class="drawer-content">
        <el-scrollbar>
          <div class="scroll-content">
            <div class="title">
              {{ $t('embedded.set_data_source') }}
            </div>

            <el-form
              ref="dsFormRef"
              :model="dsForm"
              label-width="180px"
              label-position="top"
              :rules="dsRules"
              class="form-content_error"
              @submit.prevent
            >
              <!-- <el-form-item prop="oid" :label="t('user.workspace')">
                <el-select
                  v-model="dsForm.oid"
                  filterable
                  :placeholder="
                    $t('datasource.please_enter') + $t('common.empty') + $t('user.workspace')
                  "
                  @change="wsChanged"
                >
                  <el-option
                    v-for="item in workspaces"
                    :key="item.id"
                    :label="item.name"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item> -->

              <el-form-item class="private-list_form">
                <template #label>
                  <div class="private-list">
                    {{ t('embedded.set_data_source') }}
                    <span :title="$t('embedded.open_the_query')" class="open-the_query ellipsis"
                      >{{ $t('embedded.open_the_query') }}
                    </span>
                  </div>
                </template>
                <div class="card-ds_content">
                  <DsCard
                    v-for="(ele, index) in dsListOptions"
                    :id="ele.id"
                    :key="ele.id"
                    :class="[0, 1].includes(index) && 'no-margin_top'"
                    :name="ele.name"
                    :type="ele.type"
                    :type-name="ele.type_name"
                    :description="ele.description"
                    :is-private="!dsForm.public_list.includes(ele.id)"
                    :num="ele.num"
                    @active="handleActive(ele)"
                    @private="handlePrivate(ele)"
                    @public="handlePublic(ele)"
                  ></DsCard>
                </div>
              </el-form-item>

              <el-form-item prop="auto_ds" :label="t('embedded.auto_select_ds')">
                <el-switch v-model="dsForm.auto_ds" />
              </el-form-item>
            </el-form>
          </div>
        </el-scrollbar>
      </div>

      <template #footer>
        <el-button secondary @click="beforeClose"> {{ $t('common.cancel') }} </el-button>
        <el-button v-if="activeStep === 1 && editRule !== 2" secondary @click="preview">
          {{ t('ds.previous') }}
        </el-button>
        <el-button v-if="activeStep === 0 && editRule !== 2" type="primary" @click="next">
          {{ t('common.next') }}
        </el-button>
        <el-button v-if="activeStep === 1" type="primary" @click="saveEmbedded">
          {{ $t('common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </div>
  <el-dialog
    v-model="dialogVisible"
    :title="$t('embedded.embed_third_party')"
    width="600"
    modal-class="embed-third_party"
  >
    <div class="floating-window">
      <div class="mode">
        <div
          class="floating"
          :class="activeMode === 'full' && 'active'"
          @click="activeMode = 'full'"
        >
          <div class="title">{{ $t('professional.full_screen_mode') }}</div>
          <img :src="full_window" width="180px" height="120px" alt="" />
        </div>
        <div
          class="floating"
          :class="activeMode === 'floating' && 'active'"
          @click="activeMode = 'floating'"
        >
          <div class="title">{{ $t('embedded.floating_window_mode') }}</div>
          <img :src="floating_window" width="180px" height="120px" alt="" />
        </div>
      </div>
      <div v-if="activeMode === 'floating'" class="code-bg">
        <div class="code">
          <div class="copy">
            {{ $t('embedded.code_to_embed') }}
            <el-tooltip :offset="12" effect="dark" :content="t('datasource.copy')" placement="top">
              <el-icon size="16" @click="copyCode">
                <icon_copy_outlined></icon_copy_outlined>
              </el-icon>
            </el-tooltip>
          </div>

          <div class="script">
            {{ scriptElement }}
          </div>
        </div>
        <div class="line"></div>

        <div class="code">
          <div class="copy">
            {{ $t('professional.code_for_debugging') }}
            <el-tooltip :offset="12" effect="dark" :content="t('datasource.copy')" placement="top">
              <el-icon size="16" @click="copyJsCode">
                <icon_copy_outlined></icon_copy_outlined>
              </el-icon>
            </el-tooltip>
          </div>

          <div class="script">
            {{ jsCodeElement }}
          </div>
        </div>
      </div>
      <div v-else class="code-bg">
        <div class="code">
          <div class="copy">
            {{ $t('embedded.code_to_embed') }}
            <el-tooltip :offset="12" effect="dark" :content="t('datasource.copy')" placement="top">
              <el-icon size="16" @click="copyJsCodeFull">
                <icon_copy_outlined></icon_copy_outlined>
              </el-icon>
            </el-tooltip>
          </div>

          <div class="script">
            {{ jsCodeElementFull }}
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
  <el-drawer
    v-model="drawerConfigvVisible"
    :title="drawerTitle"
    modal-class="certificate-form_drawer"
    direction="rtl"
    size="600px"
    :before-close="certificateBeforeClose"
  >
    <el-form
      ref="certificateFormRef"
      :model="certificateForm"
      label-width="180px"
      label-position="top"
      :rules="certificateRules"
      class="form-content_error"
      @submit.prevent
    >
      <el-form-item prop="source" :label="t('embedded.credential_name')">
        <el-input
          v-model="certificateForm.source"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('embedded.credential_name')
          "
          autocomplete="off"
        />
      </el-form-item>
      <el-form-item prop="type" :label="t('embedded.system_credential_type')">
        <el-select
          v-model="certificateForm.type"
          :placeholder="
            $t('datasource.Please_select') +
            $t('common.empty') +
            $t('embedded.system_credential_type')
          "
        >
          <el-option v-for="item in systemCredentials" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>

      <el-form-item prop="target_key" :label="t('embedded.target_credential_name')">
        <el-input
          v-model="certificateForm.target_key"
          clearable
          :placeholder="
            $t('datasource.please_enter') +
            $t('common.empty') +
            $t('embedded.target_credential_name')
          "
          autocomplete="off"
        />
      </el-form-item>
      <el-form-item prop="target" :label="t('embedded.target_credential_location')">
        <el-select
          v-model="certificateForm.target"
          :placeholder="
            $t('datasource.Please_select') +
            $t('common.empty') +
            $t('embedded.target_credential_location')
          "
        >
          <el-option v-for="item in credentials" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>

      <el-form-item prop="target_val" :label="t('embedded.target_credential')">
        <el-input
          v-model="certificateForm.target_val"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('embedded.target_credential')
          "
          autocomplete="off"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="certificateBeforeClose">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveHandler">
          {{ $t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
  <SetUi ref="setUiRef" @refresh="handleSearch"></SetUi>
</template>

<style lang="less" scoped>
.embedded-index {
  height: 100%;
  padding: 16px 0 16px 0;

  .ed-empty_custom {
    padding-top: 200px;
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
    .title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }

    .btn-select {
      height: 32px;
      padding-left: 4px;
      padding-right: 4px;
      display: inline-flex;
      background: #ffffff;
      align-items: center;
      border: 1px solid #d9dcdf;
      border-radius: 6px;

      .is-active {
        background: var(--ed-color-primary-1a, #1cba901a);
      }

      .ed-button:not(.is-active) {
        color: #1f2329;
      }
      .ed-button.is-text {
        height: 24px;
        width: auto;
        padding: 0 8px;
        line-height: 24px;
      }
      .ed-button + .ed-button {
        margin-left: 4px;
      }
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
.embedded-drawer-fullscreen {
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

  .private-list_form {
    .ed-form-item__label:after {
      display: none;
    }
  }

  .private-list {
    display: flex;
    align-items: center;
    .open-the_query {
      color: #ff8800;
      margin-left: 4px;
      max-width: 650px;
    }
  }

  .card-ds_content {
    width: 800px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;

    .card {
      width: 392px;
      &:nth-child(even) {
        margin-right: 0;
      }
    }

    .no-margin_top {
      margin-top: 0;
    }
  }

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

    .ed-form-item {
      &:last-child {
        margin-bottom: 0;
      }
      .aes-encrypt-tips {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #ff8800;
        margin-left: 8px;
      }
    }
  }

  .drawer-content_scroll {
    overflow: hidden;
  }

  .certificate-table_form {
    .ed-form-item__label:after {
      display: none;
    }

    .title-content {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .ed-form-item__label {
      width: 100%;
      padding-right: 0;
    }

    .title-form::after {
      color: var(--ed-color-danger);
      content: '*';
      margin-left: 2px;
    }

    .btn {
      height: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 4px;
      border-radius: 6px;
      cursor: pointer;

      &:hover {
        background-color: #1f23291a;
      }
    }
  }

  .table-content {
    width: 100%;
    max-height: calc(100vh - 390px);
    overflow-y: auto;
    border: 1px solid #dee0e3;
    border-radius: 6px;
    border-top: none;

    .operation-column_text {
      .ed-button {
        color: #646a73;
        height: 24px;
      }
      .ed-button:not(.is-disabled):hover {
        background: #1f23291a;
      }
      .ed-button + .ed-button {
        margin-left: 8px;
      }
    }

    .ed-table__empty-text {
      padding-top: 0;
    }

    &.no-credentials_yet {
      border-bottom: none;
    }
  }
}

.system-embedded_user.system-embedded_user {
  padding: 0;
  width: 282px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .popover {
    .popover-content {
      padding: 4px;
      position: relative;
    }
    .popover-item {
      min-height: 98px;
      display: flex;
      padding-left: 8px;
      padding-right: 8px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      padding-top: 8px;
      &:hover {
        background: #1f23291a;
      }

      &:nth-child(2) {
        margin: 9px 0 0 0;
      }

      .embedded {
        font-weight: 400;
        margin-left: 8px;

        .name {
          font-size: 14px;
          line-height: 22px;
        }

        .tip {
          color: #8f959e;
          font-family: PingFang SC;
          font-size: 12px;
          line-height: 20px;
        }
      }
    }
  }
}

.embed-third_party {
  .floating-window {
    width: 552px;
    .mode {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .code-bg {
      background: #f5f6f7;
      border-radius: 6px;
      overflow: hidden;
      margin-top: 16px;
    }

    .floating {
      padding: 16px;
      padding-bottom: 0;
      border-radius: 6px;
      border: 1px solid #dee0e3;
      cursor: pointer;
      width: 268px;
      height: 182px;
      display: flex;
      align-items: center;
      flex-direction: column;

      .title {
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
        margin-bottom: 8px;
      }

      &.active {
        background: var(--ed-color-primary-1a, #1cba901a);
        border-color: var(--ed-color-primary, #1cba90);
      }
    }
    .line {
      background-color: #1f232926;
      width: calc(100% - 32px);
      height: 1px;
      margin-left: 16px;
    }

    .code {
      padding: 16px;
      .copy {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;

        .ed-icon {
          cursor: pointer;
          position: relative;
          &:hover {
            &::after {
              content: '';
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              background: #1f23291a;
              width: 24px;
              height: 24px;
              border-radius: 6px;
            }
          }
        }
      }

      .script {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
      }
    }
  }
}
</style>
