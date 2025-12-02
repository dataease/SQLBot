<template>
  <div class="authentication">
    <p class="router-title">{{ t('system.authentication_settings') }}</p>
    <div v-loading="loading" class="authentication-content">
      <div class="auth-card-container">
        <div v-for="item in showInfos" :key="item.name" class="authentication-card">
          <div class="inner-card">
            <div class="inner-card-info">
              <span class="card-info-left">
                <span class="card-span">{{
                  item.name === 'oauth2' ? 'OAuth2' : item.name.toLocaleUpperCase()
                }}</span>
                <span
                  class="card-status"
                  :class="{
                    'card-hidden-status': !item.id,
                    'valid-status': item.id && item.valid,
                  }"
                  >{{ item.valid ? t('authentication.valid') : t('authentication.invalid') }}</span
                >
              </span>
              <el-tooltip
                v-if="!item.valid"
                class="box-item"
                effect="dark"
                :content="t('authentication.be_turned_on')"
                placement="top"
              >
                <el-switch
                  v-model="item.enable"
                  :disabled="!item.valid"
                  @change="switchEnable(item)"
                />
              </el-tooltip>
              <el-switch v-else v-model="item.enable" @change="switchEnable(item)" />
            </div>
            <div class="inner-card-btn">
              <el-button secondary @click="editInfo(item)">{{ t('datasource.edit') }}</el-button>
              <el-button class="card-validate-btn" secondary @click="validate(item.id)">{{
                t('ds.test_connection')
              }}</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <cas-editor ref="casEdit" @saved="init" />
    <oidc-editor ref="oidcEdit" @saved="init" />
    <ldap-editor ref="ldapEdit" @saved="init" />
    <oauth2-editor ref="oauth2Edit" @saved="init" />
    <saml2-editor ref="saml2Edit" @saved="init" />
  </div>
</template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { ref } from 'vue'
import { request } from '@/utils/request'
import CasEditor from './CasEditor.vue'
import LdapEditor from './LdapEditor.vue'
import OidcEditor from './OidcEditor.vue'
import Oauth2Editor from './Oauth2Editor.vue'
import Saml2Editor from './SAML2Editor.vue'
import { ElMessage } from 'element-plus-secondary'

const { t } = useI18n()
const loading = ref(false)
interface CardInfo {
  id: string
  name: string
  valid: boolean
  enable: boolean
}
const casEdit = ref()
const oidcEdit = ref()
const oauth2Edit = ref()
const saml2Edit = ref()
const ldapEdit = ref()
const infos = ref([] as CardInfo[])

const showInfos = ref([] as CardInfo[])

const init = (needLoading: boolean) => {
  if (needLoading) {
    loading.value = true
  }

  const url = '/system/authentication'
  request
    .get(url)
    .then((res) => {
      if (res) {
        const templateArray = ['ldap', 'oidc', 'cas', 'oauth2']
        const resultList = [...(res as CardInfo[])].filter((item) => item.name !== 'saml2')
        let resultMap = {} as any
        resultList.forEach((item: any) => {
          resultMap[item.name] = item
        })
        infos.value = templateArray.map((item: string) => resultMap[item])
        showInfos.value = [...infos.value]
      }
      loading.value = false
    })
    .catch((e) => {
      console.error(e)
      loading.value = false
    })
}
const switchEnable = (item: CardInfo) => {
  const url = '/system/authentication/enable'
  const data = { id: item.id, enable: item.enable }
  loading.value = true
  request
    .patch(url, data)
    .then(() => {
      init(false)
    })
    .catch((e) => {
      console.error(e)
    })
    .finally(() => {
      loading.value = false
    })
}
const editInfo = (item: CardInfo) => {
  if (item.name === 'oidc') {
    oidcEdit.value?.edit()
  } else if (item.name === 'cas') {
    casEdit.value?.edit()
  } else if (item.name === 'ldap') {
    ldapEdit.value?.edit()
  } else if (item.name === 'oauth2') {
    oauth2Edit.value?.edit()
  } else if (item.name === 'saml2') {
    saml2Edit.value?.edit()
  }
}
const validate = (id: any) => {
  loading.value = true
  request
    .patch('/system/authentication/status', { type: id, name: '', config: '' })
    .then((res) => {
      if (res) {
        ElMessage.success(t('ds.connection_success'))
      } else {
        ElMessage.error(t('ds.connection_failed'))
      }
      init(false)
    })
    .finally(() => {
      loading.value = false
    })
}
init(true)
</script>

<style lang="less" scoped>
.authentication {
  position: relative;
  height: 100%;
  .router-title {
    color: #1f2329;
    font-feature-settings:
      'clig' off,
      'liga' off;
    font-family: var(--de-custom_font, 'PingFang');
    font-size: 20px;
    font-style: normal;
    font-weight: 500;
    line-height: 28px;
  }
  .authentication-content {
    padding: 16px 0 24px 0;
    width: 100%;
    height: calc(100% - 28px);
  }
  .auth-card-container {
    height: initial;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;

    .authentication-card {
      width: calc(25% - 12px);
      min-width: 230px;
      height: 116px;
      padding: 24px;
      border-radius: 12px;
      background-color: #fff;
      border: 1px solid #dee0e3;
      .inner-card {
        position: relative;
        .inner-card-info {
          height: 24px;
          display: flex;
          align-items: center;
          .card-info-left {
            width: calc(100% - 40px);
            .card-span {
              font-family: var(--de-custom_font, 'PingFang');
              font-size: 16px;
              font-weight: 500;
              line-height: 24px;
              text-align: left;
            }
            .card-hidden-status {
              display: none;
            }
            .valid-status {
              background-color: #34c72433 !important;
              color: #2ca91f !important;
            }
            .card-status {
              margin-left: 8px;
              padding: 1px 6px;
              border-radius: 2px;
              background-color: #f54a4533;
              color: #d03f3b;
              line-height: 22px;
              font-size: 14px;
              font-weight: 400;
            }
          }
          .ed-switch {
            height: 22px;
          }
        }
        .inner-card-btn {
          float: left;
          height: 28px;
          margin-top: 16px;
          button {
            height: 28px;
            min-width: 46px !important;
            padding: 4px 11px !important;
            :deep(span) {
              height: 20px !important;
              line-height: 20px !important;
              font-size: 12px !important;
              display: inline-block;
              vertical-align: middle;
            }
          }
          .card-validate-btn {
            margin-left: 8px;
          }
        }
      }
    }
  }
}
</style>
