<script setup lang="ts">
import { type CanvasItem } from '@/utils/canvas.ts'
import { ref, toRefs, type PropType, computed } from 'vue'
import ResizeHandle from '@/views/dashboard/canvas/ResizeHandle.vue'
import DragHandle from '@/views/dashboard/canvas/DragHandle.vue'
import ComponentBar from '@/views/dashboard/canvas/ComponentBar.vue'
const emits = defineEmits(['enlargeView'])
const shapeRef = ref(null)
// Props
const props = defineProps({
  configItem: {
    type: Object as PropType<CanvasItem>,
    required: true,
  },
  canEdit: {
    type: Boolean,
    default: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
  itemIndex: {
    type: Number,
    required: true,
  },
  moveAnimate: {
    type: Boolean,
    required: true,
  },
  draggable: {
    type: Boolean,
    required: true,
  },
  startMove: {
    type: Function,
    default: () => {
      return {}
    },
  },
  startResize: {
    type: Function,
    default: () => {
      return {}
    },
  },
  canvasId: {
    type: String,
    default: 'canvas-main',
  },
})

const { draggable } = toRefs(props)
const shapeClick = (e: MouseEvent) => {
  // Do not stopPropagation here: the click must reach window so components that
  // rely on a window-level click listener (e.g. the S2 table copy interaction,
  // which only enables Cmd/Ctrl+C when the last click landed on its canvas) work
  // inside the editor. Deselection is handled by containerClick ignoring clicks
  // that originate inside a component.
  e.preventDefault()
}

const dragDandleValue = computed(() => props.canEdit && !props.configItem.editing)
</script>

<template>
  <div
    ref="shapeRef"
    :class="{
      item: true,
      itemActive: active,
      itemCursorDefault: configItem.component === 'SQTab',
      moveAnimation: moveAnimate,
      movingItem: configItem.isPlayer,
      canNotDrag: !draggable,
    }"
    @click="shapeClick"
    @mousedown="startMove($event, configItem, itemIndex)"
  >
    <component-bar
      :config-item="configItem"
      :active="active && canEdit"
      :show-position="'canvas'"
      :canvas-id="canvasId"
      @enlarge-view="() => emits('enlargeView')"
    ></component-bar>
    <template v-if="dragDandleValue">
      <drag-handle></drag-handle>
    </template>
    <slot></slot>
    <resize-handle
      v-if="active && canEdit"
      :start-resize="
        (event: MouseEvent, point: string) => startResize(event, point, configItem, itemIndex)
      "
    >
    </resize-handle>
  </div>
</template>

<style scoped lang="less">
@import '../css/CanvasStyle.less';
</style>
