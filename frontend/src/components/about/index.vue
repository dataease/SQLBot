<script lang="ts" setup>
import aboutBg from '@/assets/embedded/LOGO-about.png'

import { ref, reactive, onMounted } from 'vue'
import type { F2CLicense } from './index.ts'
import { licenseApi } from '@/api/license'
import { ElMessage } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user.ts'
const dialogVisible = ref(false)
const { t } = useI18n()
const userStore = useUserStore()
const license: F2CLicense = reactive({
  status: '',
  corporation: '',
  expired: '',
  count: 0,
  version: '',
  edition: '',
  serialNo: '',
  remark: '',
  isv: '',
})
const tipsSuffix = ref('')
const build = ref('')
const isAdmin = ref(false)
const fileList = reactive([])
const dynamicCardClass = ref('')
const loading = ref(false)
onMounted(() => {
  isAdmin.value = userStore.getUid === '1'
  initVersion()
  getLicenseInfo()
})

const initVersion = () => {
  licenseApi.version().then((res) => {
    build.value = res
  })
}
const beforeUpload = (file: any) => {
  importLic(file)
  return false
}

const getLicenseInfo = () => {
  validateHandler((res: any) => {
    const info = getLicense(res)
    setLicense(info)
  })
}
const setLicense = (lic: any) => {
  const lic_obj = {
    status: lic.status,
    corporation: lic.corporation,
    expired: lic.expired,
    count: lic.count,
    version: lic.version,
    edition: lic.edition,
    serialNo: lic.serialNo,
    remark: lic.remark,
    isv: lic.isv,
  }
  Object.assign(license, lic_obj)
  if (license?.serialNo && license?.remark) {
    dynamicCardClass.value = 'about-card-max'
  } else if (!license?.serialNo && !license?.remark) {
    dynamicCardClass.value = ''
  } else {
    dynamicCardClass.value = 'about-card-medium'
  }
}
const removeDistributeModule = () => {
  const key = 'xpack-model-distributed'
  localStorage.removeItem(key)
}
const importLic = (file: any) => {
  removeDistributeModule()
  const reader = new FileReader()
  reader.onload = function (e: any) {
    const licKey = e.target.result
    update(licKey)
  }
  reader.readAsText(file)
}
const validateHandler = (success: any) => {
  licenseApi.validate().then(success)
}
const getLicense = (result: any) => {
  if (result.status === 'valid') {
    tipsSuffix.value = result?.license?.edition === 'Embedded' ? '套' : '个账号'
  }
  return {
    status: result.status,
    corporation: result.license ? result.license.corporation : '',
    expired: result.license ? result.license.expired : '',
    count: result.license ? result.license.count : 0,
    version: result.license ? result.license.version : '',
    edition: result.license ? result.license.edition : '',
    serialNo: result.license ? result.license.serialNo : '',
    remark: result.license ? result.license.remark : '',
    isv: result.license ? result.license.isv : '',
  }
}
const update = (licKey: string) => {
  const param = { license_key: licKey }
  loading.value = true
  licenseApi.update(param).then((response: any) => {
    loading.value = false
    if (response.status === 'valid') {
      ElMessage.success(t('about.update_success'))
      const info = getLicense(response)
      setLicense(info)
    } else {
      ElMessage.warning(response.message)
    }
  })
}

const open = () => {
  dialogVisible.value = true
  getLicenseInfo()
}

defineExpose({
  open,
})
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="t('about.title')"
    width="840px"
    modal-class="about-dialog"
  >
    <div class="color-overlay flex-center">
      <img width="368" height="84" :src="aboutBg" />
    </div>
    <div class="content">
      <div class="item">
        <div class="label">{{ $t('about.auth_to') }}</div>
        <div class="value">{{ license.corporation }}</div>
      </div>
      <div v-if="license.isv" class="item">
        <div class="label">ISV</div>
        <div class="value">{{ license.isv }}</div>
      </div>
      <div class="item">
        <div class="label">{{ $t('about.expiration_time') }}</div>
        <div class="value" :class="{ 'expired-mark': license.status === 'expired' }">
          {{ license.expired }}
        </div>
      </div>
      <div class="item">
        <div class="label">{{ $t('about.version') }}</div>
        <div class="value">
          {{
            !license?.edition
              ? $t('about.standard')
              : license.edition === 'Embedded'
                ? $t('about.Embedded')
                : license.edition === 'Professional'
                  ? $t('about.Professional')
                  : $t('about.enterprise')
          }}
        </div>
      </div>
      <div class="item">
        <div class="label">{{ $t('about.version_num') }}</div>
        <div class="value">{{ build }}</div>
      </div>
      <div class="item">
        <div class="label">{{ $t('about.serial_no') }}</div>
        <div class="value">{{ license.serialNo || '-' }}</div>
      </div>
      <div class="item">
        <div class="label">{{ $t('about.remark') }}</div>
        <div class="value ellipsis">{{ license.remark || '-' }}</div>
      </div>

      <div v-if="isAdmin" style="margin-top: 24px" class="lic_rooter">
        <el-upload
          action=""
          :multiple="false"
          :show-file-list="false"
          :file-list="fileList"
          accept=".key"
          name="file"
          :before-upload="beforeUpload"
        >
          <el-button plain> {{ $t('about.update_license') }} </el-button>
        </el-upload>
      </div>
    </div>
    <div class="name">2014-2026 版权所有 © 杭州飞致云信息科技有限公司</div>
  </el-dialog>
</template>

<style lang="less">
.about-dialog {
  .color-overlay {
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background: var(--ed-color-primary-1a, #1cba901a);
    border: 1px solid #dee0e3;
    border-bottom: 0;
    height: 180px;
  }

  .name {
    font-weight: 400;
    font-size: 12px;
    line-height: 22px;
    text-align: center;
    margin-top: 16px;
    color: #8f959e;
  }

  .content {
    border-radius: 6px;
    border: 1px solid #dee0e3;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-top: 0;
    padding: 24px 40px;

    .item {
      font-size: 16px;
      font-style: normal;
      font-weight: 400;
      line-height: 24px;
      margin-bottom: 16px;
      display: flex;
      font-weight: 400;
      .expired-mark {
        color: red;
      }
      .label {
        color: #646a73;
        width: 240px;
      }

      .value {
        margin-left: 24px;
        max-width: 448px;
      }
    }
  }
}
.lic_rooter {
  flex-direction: row;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  align-content: center;
  width: fit-content;
  justify-content: space-between;
  column-gap: 12px;
}
</style>
