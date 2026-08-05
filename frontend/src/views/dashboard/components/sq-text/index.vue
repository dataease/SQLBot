<template>
  <div class="rich-main-class" :class="{ 'edit-model': configItem.editing }" draggable="false">
    <div
      :class="{ 'rich-text-empty': true, 'layer-hidden': !isDisabled || configItem.propValue }"
      @keydown.stop
      @keyup.stop
      @mousedown.stop
      @dblclick.stop="setEdit"
    >
      {{ t('dashboard.rich_text_tips') }}
    </div>
    <div
      draggable="false"
      :class="{ 'custom-text-content': true, 'preview-text': true, 'layer-hidden': !isDisabled }"
      @keydown.stop
      @keyup.stop
      @mousedown.stop
      @dblclick.stop="setEdit"
      v-dompurify-html="configItem.propValue"
    ></div>
    <editor
      :id="tinymceId"
      v-model="configItem.propValue"
      draggable="false"
      :class="{ 'custom-text-content': true, 'layer-hidden': isDisabled }"
      :init="init"
    ></editor>
  </div>
</template>

<script setup lang="ts">
import tinymce from 'tinymce/tinymce'
import Editor from '@tinymce/tinymce-vue'
import 'tinymce/icons/default'
import 'tinymce/plugins/link'
import '@npkg/tinymce-plugins/letterspacing'

import { computed, nextTick, type PropType, reactive, toRefs } from 'vue'
import { onMounted } from 'vue'
import type { CanvasItem } from '@/utils/canvas.ts'
import { dashboardStoreWithOut } from '@/stores/dashboard/dashboard.ts'
import { useI18n } from 'vue-i18n'
const dashboardStore = dashboardStoreWithOut()
const { t } = useI18n()

const props = defineProps({
  configItem: {
    type: Object as PropType<CanvasItem>,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const { configItem } = toRefs(props)
const tinymceId = 'vue-tinymce-' + +new Date() + ((Math.random() * 1000).toFixed(0) + '')
const init = reactive({
  base_url: '/tinymce', // 指向 public/tinymce 目录
  suffix: '.min',
  selector: tinymceId,
  language: 'zh_CN',
  skin: 'oxide',
  plugins: 'link letterspacing', // 插件
  // 工具栏
  toolbar:
    'fontfamily fontsize | |forecolor backcolor bold italic letterspacing |underline strikethrough link lineheight| formatselect | alignleft aligncenter alignright |',
  toolbar_location: '/',
  font_family_formats:
    '微软雅黑=Microsoft YaHei;宋体=SimSun;黑体=SimHei;仿宋=FangSong;华文黑体=STHeiti;华文楷体=STKaiti;华文宋体=STSong;华文仿宋=STFangsong;Andale Mono=andale mono,times;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;Comic Sans MS=comic sans ms,sans-serif;Courier New=courier new,courier;Georgia=georgia,palatino;Helvetica=helvetica;Impact=impact,chicago;Symbol=symbol;Tahoma=tahoma,arial,helvetica,sans-serif;Terminal=terminal,monaco;Times New Roman=times new roman,times;Trebuchet MS=trebuchet ms,geneva;Verdana=verdana,geneva;Webdings=webdings;Wingdings=wingdings',
  font_size_formats:
    '12px 14px 16px 18px 20px 22px 24px 28px 32px 36px 42px 48px 56px 72px 80px 90px 100px 110px 120px 140px 150px 170px 190px 210px', // 字体大小
  menubar: false,
  placeholder: '',
  inline: true,
})

const isDisabled = computed(() => props.disabled || !configItem.value.editing)

const setEdit = () => {
  configItem.value.editing = true
  dashboardStore.setCurComponent(configItem.value)
  nextTick(() => {
    editCursor()
  })
}

const editCursor = () => {
  setTimeout(() => {
    const myDiv = document.getElementById(tinymceId)
    // Focus the cursor on the end of the text
    const range = document.createRange()
    const sel = window.getSelection()
    if (myDiv && myDiv.childNodes) {
      range.setStart(myDiv.childNodes[myDiv.childNodes.length - 1], 1)
      range.collapse(false)
      if (sel) {
        sel.removeAllRanges()
        sel.addRange(range)
      }
    }
    // For some browsers, it may be necessary to set the cursor to the end in another way
    if (myDiv && myDiv.focus) {
      myDiv.focus()
    }
  }, 100)
}

onMounted(() => {
  tinymce.init({})
})
</script>
<style scoped lang="less">
.edit-model {
  cursor: text;
}

.rich-main-class {
  display: flex;
  font-size: initial;
  width: 100%;
  height: 100%;
  overflow-y: auto !important;
  position: relative;
  padding: 12px !important;
  div::-webkit-scrollbar {
    width: 0 !important;
    height: 0 !important;
  }
  .rich-text-empty {
    position: absolute;
    width: calc(100% - 24px);
    height: calc(100% - 24px);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    z-index: 10;
    color: rgba(100, 106, 115, 1);
  }
  div::-webkit-scrollbar {
    width: 0px !important;
    height: 0px !important;
  }

  :deep(.ol) {
    display: block !important;
    list-style-type: decimal;
    margin-block-start: 1em !important;
    margin-block-end: 1em !important;
    margin-inline-start: 0px !important;
    margin-inline-end: 0px !important;
    padding-inline-start: 40px !important;
  }

  :deep(ul) {
    display: block !important;
    list-style-type: disc;
    margin-block-start: 1em !important;
    margin-block-end: 1em !important;
    margin-inline-start: 0px !important;
    margin-inline-end: 0px !important;
    padding-inline-start: 40px !important;
  }

  :deep(li) {
    margin-left: 20px;
    display: list-item !important;
    text-align: -webkit-match-parent !important;
  }
}

.custom-text-content {
  width: 100%;
  overflow-y: auto;
  outline: none !important;
  border: none !important;
  margin: 2px;
  cursor: text;
  p {
    word-break: break-all;
  }

  ol {
    list-style-type: decimal;
  }
}

.layer-hidden {
  display: none !important;
}

.preview-text {
  cursor: pointer;
}
</style>
