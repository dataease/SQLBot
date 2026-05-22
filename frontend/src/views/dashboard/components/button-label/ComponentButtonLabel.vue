<script setup lang="ts">
import { toRefs } from 'vue'

const props = defineProps({
  title: { type: String, required: false, default: '' },
  tips: { type: String, required: false, default: '' },
  iconName: { type: String, required: false, default: '' },
  showSplitLine: { type: Boolean, required: false, default: false },
  active: { type: Boolean, required: false, default: false },
})

const { title, tips, iconName, showSplitLine } = toRefs(props)
const emits = defineEmits(['customClick'])
</script>

<template>
  <div class="flex-align-center">
    <el-row class="group_icon" :title="tips" @click="emits('customClick')">
      <el-col :span="24" class="group_inner" :class="{ 'inner-active': active }">
        <component :is="iconName" class="svg-icon toolbar-icon"></component>
        <span>{{ title }}</span>
      </el-col>
    </el-row>
    <el-divider v-if="showSplitLine" class="group-right-border" direction="vertical" />
  </div>
</template>
<style lang="less" scoped>
.flex-align-center {
  display: flex;
  justify-content: center;
  align-items: center;
  & + & {
    margin-left: 12px;
  }
}

.group_inner {
  padding: 4px;
  display: flex;
  cursor: pointer;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
  color: #1f2329;

  span {
    float: left;
    font-size: 14px;
    margin-left: 4px;
  }

  &:hover {
    background: rgba(31, 35, 41, 0.1);
  }

  &:active {
    background: rgba(31, 35, 41, 0.1);
  }
}

.group-right-border {
  border-color: rgba(31, 35, 41, 0.15);
  margin: 0 4px 0 16px;
  height: 14px;
}

.inner-active {
  border: 1px solid var(--ed-color-primary);
  background: rgba(255, 255, 255, 0.2);
}

.toolbar-icon {
  float: left;
  width: 20px;
  height: 20px;
}
</style>
