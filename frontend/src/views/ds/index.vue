<template>
  <div v-loading="loading">
    <div class="header">
      <div class="mt-4">
        <el-input
          v-model="searchValue"
          style="max-width: 300px"
          :placeholder="t('ds.Search Datasource')"
          class="input-with-select"
          clearable
          @change="searchHandle"
        >
          <template #prepend>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>
      </div>

      <el-button
        class="border-radius_8"
        type="primary"
        :icon="IconOpeAdd"
        @click="editDs(undefined)"
        >{{ t('ds.add') }}</el-button
      >
    </div>

    <div class="connections-container">
      <template v-for="ds in dsList" :key="ds">
        <DatasourceItemCard :ds="ds">
          <div class="connection-actions">
            <el-button class="action-btn" circle :icon="List" @click="getTables(ds.id, ds.name)" />
            <el-button
              type="primary"
              class="action-btn"
              circle
              :icon="IconOpeEdit"
              @click="editDs(ds)"
            />
            <el-button
              type="danger"
              class="action-btn"
              circle
              :icon="IconOpeDelete"
              @click="deleteDs(ds)"
            />
          </div>
        </DatasourceItemCard>
      </template>
    </div>
  </div>
  <DsForm ref="dsForm" @refresh="refresh" />
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import IconOpeAdd from '@/assets/svg/operate/ope-add.svg'
import IconOpeEdit from '@/assets/svg/operate/ope-edit.svg'
import IconOpeDelete from '@/assets/svg/operate/ope-delete.svg'
import { Search, List } from '@element-plus/icons-vue'
import DsForm from './form.vue'
import { datasourceApi } from '@/api/datasource'
import { ElMessageBox } from 'element-plus-secondary'
import { useRouter } from 'vue-router'
import DatasourceItemCard from '@/views/ds/DatasourceItemCard.vue'

const { t } = useI18n()
const searchValue = ref<string>('')
const dsForm = ref()
const dsList = ref<any>([]) // show ds list
const allDsList = ref<any>([]) // all ds list
const router = useRouter()
const loading = ref(false)

function searchHandle() {
  if (searchValue.value) {
    dsList.value = JSON.parse(JSON.stringify(allDsList.value)).filter((item: any) => {
      return item.name.toLowerCase().includes(searchValue.value.toLowerCase())
    })
  } else {
    dsList.value = JSON.parse(JSON.stringify(allDsList.value))
  }
}

const refresh = () => {
  list()
}

const list = () => {
  loading.value = true
  datasourceApi.list().then((res) => {
    allDsList.value = res
    dsList.value = JSON.parse(JSON.stringify(allDsList.value))
    loading.value = false
  })
}

const editDs = (item: any) => {
  dsForm.value.open(item)
}

const deleteDs = (item: any) => {
  ElMessageBox.confirm(t('ds.delete'), t('common.confirm'), {
    confirmButtonText: t('common.confirm'),
    cancelButtonText: t('common.cancel'),
    type: 'warning',
  })
    .then(() => {
      datasourceApi.delete(item.id, item.name).then(() => {
        refresh()
      })
    })
    .catch(() => {})
}

const getTables = (id: number, name: string) => {
  router.push(`/dsTable/${id}/${name}`)
}

onMounted(() => {
  list()
})
</script>
<style lang="less" scoped>
.header {
  background-color: white;
  padding: 16px 20px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  .input-with-select {
    --ed-input-border-radius: 8px;
    --ed-border-radius-base: 8px;
  }
}

.connections-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;

  .connection-actions {
    position: absolute;
    bottom: 20px;
    right: 20px;
    display: flex;

    .action-btn {
      display: none;
      min-width: 0;
    }
  }

  :hover .action-btn {
    display: flex;
  }
}
</style>
