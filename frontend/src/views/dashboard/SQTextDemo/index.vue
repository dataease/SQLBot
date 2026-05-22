<template>
  <div>
    <h1>文章编辑器</h1>
    <RichTextEditor v-model="articleContent" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import RichTextEditor from '@/views/dashboard/components/sq-text-t7/index.vue'
const articleContent = ref('<p>这里是默认内容...</p>')
</script>

<style>
.preview {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 6px;
}
</style>
