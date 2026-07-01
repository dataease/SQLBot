<script lang="ts" setup>
import { ref, computed } from 'vue'
import DatasourceCard from './DatasourceCard.vue'
interface Datasource {
  id?: string
  name: string
  description: string
  creator: string
}
const props = withDefaults(
  defineProps<{
    datasourceList: Array<Datasource>
  }>(),
  {
    datasourceList: () => [],
  }
)

const datasourceName = ref('')
const datasourceListComputed = computed(() =>
  props.datasourceList.filter((val) =>
    val.name.toLowerCase().includes(datasourceName.value.toLowerCase())
  )
)

const dialogVisible = ref(false)
</script>

<template>
  <div class="chat-init_tip">
    <div class="hello-sqlbot">Hello, I'm SQLBot, happy to serve you!</div>
    <div class="function-sqlbot">
      I can help you query data, generate charts, detect data anomalies, predict data, etc. Please
      select a data source and start intelligent data query~
    </div>
    <div class="select-datasource">
      <span class="title">Select data source</span>
      <el-button text @click="dialogVisible = true">View more</el-button>
    </div>
    <div class="datasource-content flex-gap-fallback">
      <DatasourceCard
        v-for="ele in datasourceList"
        :key="ele.id"
        :name="ele.name"
        :description="ele.description"
        :creator="ele.creator"
      ></DatasourceCard>
    </div>
    <el-button type="primary">Create a new data source</el-button>
  </div>
  <el-dialog
    v-model="dialogVisible"
    title="Select data source"
    width="800"
    modal-class="select-datasource_dialog"
  >
    <div class="search-datasource">
      <el-input
        v-model="datasourceName"
        clearable
        style="width: 240px"
        placeholder="Please input"
      />
    </div>
    <div class="datasource-content flex-gap-fallback">
      <DatasourceCard
        v-for="ele in datasourceListComputed"
        :key="ele.id"
        :name="ele.name"
        :description="ele.description"
        :creator="ele.creator"
      ></DatasourceCard>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="dialogVisible = false"> Confirm </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="less" scoped>
.chat-init_tip {
  width: 780px;
  padding: 16px;
  .hello-sqlbot {
    margin-bottom: 12px;
    font-size: 16px;
    font-weight: 500;
  }
  .function-sqlbot {
    margin-bottom: 12px;
  }

  .select-datasource {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .datasource-content {
    margin: 12px 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    --gap-size: 16px;
    gap: 16px;
  }
}
</style>

<style lang="less">
.select-datasource_dialog {
  .search-datasource {
    text-align: right;
  }

  .datasource-content {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    --gap-size: 16px;
    gap: 16px;
    margin-top: 16px;
  }
}
</style>
