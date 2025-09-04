<script setup lang="ts">
import { ref, nextTick, toRefs, type PropType, onMounted, getCurrentInstance } from 'vue'
import _ from 'lodash'
import { dashboardStoreWithOut } from '@/stores/dashboard/dashboard'
import { type CanvasCoord, type CanvasItem } from '@/utils/canvas.ts'
import CanvasShape from './CanvasShape.vue'
import { findComponent } from '@/views/dashboard/components/component-list.ts'
import { storeToRefs } from 'pinia'
import { useEmitt, useEmittLazy } from '@/utils/useEmitt.ts'
import html2canvas from 'html2canvas'
import EmptyBackground from '@/views/dashboard/common/EmptyBackgroundSvgMain.vue'
import { useI18n } from 'vue-i18n'
import { isMainCanvas } from '@/views/dashboard/utils/canvasUtils.ts'

const { t } = useI18n()
const dashboardStore = dashboardStoreWithOut()
const canvasLocked = ref(false) // Is the canvas movement locked， Default false
const emits = defineEmits(['parentAddItemBox'])
const { curComponentId, curComponent, fullscreenFlag } = storeToRefs(dashboardStore)
let currentInstance: any
const props = defineProps({
  canvasId: {
    type: String,
    default: 'canvas-main',
  },
  parentConfigItem: {
    type: Object as PropType<CanvasItem>,
    required: false,
    default: null,
  },
  dashboardInfo: {
    type: Object,
    required: false,
    default: () => {},
  },
  canvasStyleData: {
    type: Object,
    required: false,
    default: () => {},
  },
  canvasViewInfo: {
    type: Object,
    required: false,
    default: () => {},
  },
  canvasComponentData: {
    type: Array as PropType<CanvasItem[]>,
    required: true,
  },
  baseWidth: {
    type: Number,
    default: 100,
  },
  baseHeight: {
    type: Number,
    default: 50,
  },
  baseMarginLeft: {
    type: Number,
    default: 20,
  },
  baseMarginTop: {
    type: Number,
    default: 20,
  },
  draggable: {
    type: Boolean,
    default: true,
  },
  dragStart: {
    type: Function,
    default: () => {
      return {}
    },
  },
  dragging: {
    type: Function,
    default: () => {
      return {}
    },
  },
  dragEnd: {
    type: Function,
    default: () => {
      return {}
    },
  },
  resizable: {
    type: Boolean,
    default: true,
  },
  resizeStart: {
    type: Function,
    default: () => {
      return {}
    },
  },
  resizing: {
    type: Function,
    default: () => {
      return {}
    },
  },
  resizeEnd: {
    type: Function,
    default: () => {
      return {}
    },
  },
})

const {
  canvasComponentData,
  baseWidth,
  baseHeight,
  baseMarginLeft,
  baseMarginTop,
  draggable,
  resizable,
} = toRefs(props)

// DOM ref
const containerRef = ref<HTMLElement | null>(null)
const renderOk = ref(false)
const moveAnimate = ref(false)
const cellWidth = ref(0)
const cellHeight = ref(0)
const maxCell = ref(0)
const positionBox = ref<Array<Array<{ el: boolean }>>>([])
const coordinates = ref<CanvasCoord[]>([])
const infoBox = ref()

// Position data (non-reactive)
let lastTask: (() => void) | undefined = undefined
let isOverlay = false
let itemMaxX = 0
let itemMaxY = 0
const moveTime = 80

const tabMoveInYOffset = 30
const tabMoveOutXOffset = 30
const tabMoveOutYOffset = 30
// Effective area of collision depth
const collisionGap = 10

function debounce(func: () => void, time: number) {
  if (!isOverlay) {
    isOverlay = true
    setTimeout(() => {
      func()
      setTimeout(() => {
        isOverlay = false
        if (lastTask !== undefined) {
          const nextTask = lastTask
          lastTask = undefined
          debounce(nextTask, time)
        }
      }, moveTime)
    }, time)
    lastTask = undefined
  } else {
    lastTask = func
  }
}

function scrollScreen(e: MouseEvent) {
  const scrollStep = 20
  const bufferBottom = 50
  const bufferTop = 150
  if (e.clientY + bufferBottom >= window.innerHeight) {
    document.documentElement.scrollTop += scrollStep
  } else if (e.clientY <= bufferTop) {
    document.documentElement.scrollTop -= scrollStep
  }
}

/**
 * Reset Position Box
 */
function resetPositionBox() {
  itemMaxX = maxCell.value
  const rows = 1 // Set only one line initially
  for (let i = 0; i < rows; i++) {
    const row = []
    for (let j = 0; j < maxCell.value; j++) {
      row.push({ el: false })
    }
    positionBox.value.push(row)
  }
}

/**
 * Fill Position Box
 *
 * @param {CanvasItem} item
 */
function addItemToPositionBox(item: CanvasItem) {
  const pb = positionBox.value
  if (item.x <= 0 || item.y <= 0) return
  // Traverse the grid at the target location and add the item to it
  for (let i = item.x - 1; i < item.x - 1 + item.sizeX; i++) {
    for (let j = item.y - 1; j < item.y - 1 + item.sizeY; j++) {
      if (pb[j] && pb[j][i]) {
        // Ensure the target location is valid & Place the item in the corresponding position
        // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
        pb[j][i].el = item
      }
    }
  }
}

function fillPositionBox(maxY: number) {
  const pb = positionBox.value
  maxY += 2
  for (let j = 0; j < maxY; j++) {
    if (pb[j] === undefined) {
      const row = []
      for (let i = 0; i < itemMaxX; i++) {
        row.push({ el: false })
      }
      pb.push(row)
    }
  }
  itemMaxY = maxY
  // Update container height
  if (containerRef.value) {
    containerRef.value.style.height = `${(itemMaxY + 2) * cellHeight.value}px`
  }
}

/**
 * Remove item from positionBox
 * @param item
 */
function removeItemFromPositionBox(item: CanvasItem) {
  const pb = positionBox.value
  if (item.x <= 0 || item.y <= 0) return
  // Traverse the area occupied by the item and remove it
  for (let i = item.x - 1; i < item.x - 1 + item.sizeX; i++) {
    for (let j = item.y - 1; j < item.y - 1 + item.sizeY; j++) {
      if (pb[j] && pb[j][i]) {
        // Ensure the target location is valid
        pb[j][i].el = false // Remove item and set it to false or null
      }
    }
  }
}

/**
 * Recalculate the width so that the smallest cell can fill the entire container
 */
function recomputeCellWidth() {
  if (!containerRef.value) return
  maxCell.value = Math.floor(containerRef.value.offsetWidth / cellWidth.value)
}

function sizeInit() {
  cellsInit()
  recomputeCellWidth()
  itemMaxX = maxCell.value
}

function cellsInit() {
  cellWidth.value = baseWidth.value + baseMarginLeft.value
  cellHeight.value = baseHeight.value + baseMarginTop.value
}

function init() {
  cellsInit()

  positionBox.value = []
  coordinates.value = []

  lastTask = undefined
  isOverlay = false
  itemMaxX = 0
  itemMaxY = 0

  recomputeCellWidth()
  resetPositionBox()

  let i = 0
  const timeId = setInterval(() => {
    if (i >= canvasComponentData.value.length) {
      clearInterval(timeId)
      nextTick(() => {
        moveAnimate.value = true
      })
    } else {
      const item = canvasComponentData.value[i]
      addItem(item, i)
      i++
    }
  }, 1)
  renderOk.value = true
}

function resizePlayer(item: CanvasItem, newSize: any) {
  removeItemFromPositionBox(item)
  const belowItems = findBelowItems(item) as CanvasItem[]
  _.forEach(belowItems, (upItem) => {
    const canGoUpRows = canItemGoUp(upItem)
    if (canGoUpRows > 0) {
      moveItemUp(upItem, canGoUpRows)
    }
  })

  item.sizeX = newSize.sizeX
  item.sizeY = newSize.sizeY

  if (item.sizeX + item.x - 1 > itemMaxX) {
    item.sizeX = itemMaxX - item.x + 1
  }

  if (item.sizeY + item.y > itemMaxY) {
    fillPositionBox(item.y + item.sizeY)
  }

  // Move the current item
  item.x = newSize.x
  item.y = newSize.y

  emptyTargetCell(item)
  addItemToPositionBox(item)
  changeItemCoord(item)

  const canGoUpRows = canItemGoUp(item)
  if (canGoUpRows > 0) {
    moveItemUp(item, canGoUpRows)
  }
  if (item.component === 'SQView') {
    useEmittLazy(`view-render-${item.id}`)
  }
}

/**
 * Check the position of the movement, if it is illegal, it will be automatically modified
 *
 * @param {CanvasItem} item
 * @param {any} position
 */
function checkItemPosition(item: CanvasItem, position: Partial<{ x: number; y: number }> = {}) {
  position.x = position.x || item.x
  position.y = position.y || item.y

  // Limit minimum coordinates
  if (item.x < 1) item.x = 1
  if (item.y < 1) item.y = 1

  // Limit minimum size
  if (item.sizeX < 1) item.sizeX = 1
  if (item.sizeY < 1) item.sizeY = 1

  // Limit maximum width
  if (item.sizeX > itemMaxX) item.sizeX = itemMaxX

  // Limit the right side to not exceed the boundary
  if (item.x + item.sizeX - 1 > itemMaxX) {
    item.x = itemMaxX - item.sizeX + 1
    if (item.x < 1) item.x = 1
  }

  // If the height of the item exceeds the current maximum number of rows, fill the position table
  if (item.y + item.sizeY > itemMaxY - 1) {
    fillPositionBox(item.y + item.sizeY - 1)
  }
}

/**
 * Move the element being dragged
 *
 * @param {CanvasItem} item
 * @param {any} position
 */
function movePlayer(item: CanvasItem, position: any) {
  // Remove item location
  removeItemFromPositionBox(item)
  // Find the item below
  let belowItems = findBelowItems(item) as CanvasItem[]
  // Traverse the items below and move them
  belowItems.forEach((upItem) => {
    const canGoUpRows = canItemGoUp(upItem)
    if (canGoUpRows > 0) {
      moveItemUp(upItem, canGoUpRows)
    }
  })
  // Move the current item
  item.x = position.x
  item.y = position.y

  // Check and update the location of items
  checkItemPosition(item, position)
  // Clear the target cell
  emptyTargetCell(item)
  // Add items to the location box
  addItemToPositionBox(item)
  // Modify item coordinates
  changeItemCoord(item)
  // Recheck if the item can be moved up again
  const canGoUpRows = canItemGoUp(item)
  if (canGoUpRows > 0) {
    moveItemUp(item, canGoUpRows)
  }
}

function removeItemById(id: number) {
  const index = canvasComponentData.value.findIndex((item) => item.id === id)
  if (index >= 0) {
    removeItem(index)
    renderOk.value = false
    nextTick(() => {
      renderOk.value = true
    })
  }
}

function removeItem(index: number) {
  const item = canvasComponentData.value[index] as CanvasItem
  removeItemFromPositionBox(item)
  const belowItems = findBelowItems(item) as CanvasItem[]
  belowItems.forEach((upItem) => {
    const canGoUpRows = canItemGoUp(upItem)
    if (canGoUpRows > 0) {
      moveItemUp(upItem, canGoUpRows)
    }
  })
  canvasComponentData.value.splice(index, 1)
}

function getNextDragId() {
  if (!canvasComponentData.value || canvasComponentData.value.length === 0) {
    return 0
  }
  const validIds = canvasComponentData.value
    .map((item) => item._dragId)
    .filter((id) => id != null && id !== '') // 过滤 null、undefined 和空字符串

  if (validIds.length === 0) {
    return 0
  }
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  const maxDragId = Math.max(...validIds)
  return maxDragId + 1
}

function addItem(item: CanvasItem, index: any) {
  if (index < 0) {
    index = canvasComponentData.value.length
  }
  item._dragId = item.id || getNextDragId()
  checkItemPosition(item, { x: item.x, y: item.y })
  emptyTargetCell(item)
  addItemToPositionBox(item)
  const canGoUpRows = canItemGoUp(item)
  if (canGoUpRows > 0) {
    moveItemUp(item, canGoUpRows)
  }
  // makeCoordinate(item) // If coordinate points need to be generated, untangle the annotations
}

function changeToCoord(left: number, top: number, width: number, height: number) {
  return {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2,
  }
}

/**
 * Detect for collisions and take appropriate measures
 *
 * @param {CanvasItem} item comparison object
 * @param {CanvasCoord} tCoord compares the coordinates of the object
 */
function findClosetCoords(item: CanvasItem, tCoord: CanvasCoord) {
  if (isOverlay) return
  let collisionsItem: { centerDistance: number; coord: CanvasCoord }[] = []
  coordinates.value.forEach((nowCoord) => {
    // Avoid comparing yourself to others
    if (item._dragId === nowCoord.el._dragId) {
      return
    }
    // Determine whether a collision has occurred
    if (
      tCoord.x2 < nowCoord.x1 ||
      tCoord.x1 > nowCoord.x2 ||
      tCoord.y2 < nowCoord.y1 ||
      tCoord.y1 > nowCoord.y2
    ) {
      return
    } else {
      collisionsItem.push({
        centerDistance: Math.sqrt(
          Math.pow(tCoord.c1 - nowCoord.c1, 2) + Math.pow(tCoord.c2 - nowCoord.c2, 2)
        ),
        coord: nowCoord,
      })
    }
  })
  if (collisionsItem.length <= 0) {
    return
  }
  isOverlay = true
  collisionsItem = collisionsItem.sort((a, b) => a.centerDistance - b.centerDistance)
  movePlayer(item, {
    x: collisionsItem[0].coord.el.x,
    y: collisionsItem[0].coord.el.y,
  })

  setTimeout(() => {
    isOverlay = false
  }, 200)
}

/**
 * Generate coordinates
 * @param item
 */
function makeCoordinate(item: CanvasItem) {
  let width = cellWidth.value * item.sizeX - baseMarginLeft.value
  let height = cellHeight.value * item.sizeY - baseMarginTop.value
  let left = cellWidth.value * (item.x - 1) + baseMarginLeft.value
  let top = cellHeight.value * (item.y - 1) + baseMarginTop.value

  let coord = {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2,
    el: item,
  }

  coordinates.value.push(coord)
}

/**
 * Change the coordinates of the item
 * @param item
 */
function changeItemCoord(item: CanvasItem) {
  let width = cellWidth.value * item.sizeX - baseMarginLeft.value
  let height = cellHeight.value * item.sizeY - baseMarginTop.value
  let left = cellWidth.value * (item.x - 1) + baseMarginLeft.value
  let top = cellHeight.value * (item.y - 1) + baseMarginTop.value

  let coord = {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2,
    el: item,
  }

  // Find and update the corresponding coordinates
  const index = coordinates.value.findIndex((o) => o.el._dragId === item._dragId)
  if (index !== -1) {
    coordinates.value.splice(index, 1, coord)
  }
}

/**
 * Clear the elements at the target location
 * @param {any} item Target item
 */
function emptyTargetCell(item: CanvasItem) {
  let belowItems = findBelowItems(item) as CanvasItem[]

  belowItems.forEach((downItem) => {
    if (downItem._dragId === item._dragId) return
    let moveSize = item.y + item.sizeY - downItem.y
    if (moveSize > 0) {
      moveItemDown(downItem, moveSize)
    }
  })
}

/**
 * Can the item at the current location float up
 * @param {CanvasItem} item Current item
 */
function canItemGoUp(item: CanvasItem) {
  let upperRows = 0
  for (let row = item.y - 2; row >= 0; row--) {
    for (let cell = item.x - 1; cell < item.x - 1 + item.sizeX; cell++) {
      if (
        positionBox.value[row] &&
        positionBox.value[row][cell] &&
        positionBox.value[row][cell].el
      ) {
        return upperRows
      }
    }
    upperRows++
  }

  return upperRows
}

/**
 * Before moving, find the element below the currently moving element (recursively)
 *
 * @param {CanvasItem} item
 * @param {number} size
 */
function moveItemDown(item: CanvasItem, size: number) {
  removeItemFromPositionBox(item)

  const belowItems = findBelowItems(item) as CanvasItem[]

  for (const downItem of belowItems) {
    if (downItem._dragId === item._dragId) continue

    const moveSize = calcDiff(item, downItem, size)
    if (moveSize > 0) {
      moveItemDown(downItem, moveSize)
    }
  }

  const targetPosition = {
    y: item.y + size,
  }

  setPlayerPosition(item, targetPosition)
  checkItemPosition(item, targetPosition)

  addItemToPositionBox(item)
  changeItemCoord(item)
}

function setPlayerPosition(item: CanvasItem, position: { x?: number; y?: number } = {}) {
  const targetX = position.x || item.x
  const targetY = position.y || item.y

  item.x = targetX
  item.y = targetY

  if (item.y + item.sizeY > itemMaxY) {
    itemMaxY = item.y + item.sizeY
  }
}

/**
 * Find the maximum distance from a child element to its parent element
 *
 * @param {CanvasItem} parent
 * @param {CanvasItem} son
 * @param {number} size
 */
function calcDiff(parent: CanvasItem, son: CanvasItem, size: number) {
  const diffs = []

  for (let i = son.x - 1; i < son.x - 1 + son.sizeX; i++) {
    let temp_y = 0

    for (let j = parent.y - 1 + parent.sizeY; j < son.y - 1; j++) {
      if (positionBox.value[j][i] && positionBox.value[j][i].el === false) {
        temp_y++
      }
    }

    diffs.push(temp_y)
  }

  const max_diff = Math.max(...diffs)
  size = size - max_diff

  return size > 0 ? size : 0
}

function moveItemUp(item: CanvasItem, size: number) {
  removeItemFromPositionBox(item)

  const belowItems = findBelowItems(item) as CanvasItem[]

  setPlayerPosition(item, {
    y: item.y - size,
  })

  addItemToPositionBox(item)

  changeItemCoord(item)

  for (const upItem of belowItems) {
    const moveSize = canItemGoUp(upItem)
    if (moveSize > 0) {
      moveItemUp(upItem, moveSize)
    }
  }
}

function findBelowItems(item: CanvasItem) {
  const belowItems = {}

  for (let cell = item.x - 1; cell < item.x - 1 + item.sizeX; cell++) {
    for (let row = item.y - 1; row < positionBox.value.length; row++) {
      const target = positionBox.value[row][cell]
      if (target && target.el) {
        // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
        belowItems[target.el._dragId] = target.el
        break
      }
    }
  }

  return _.sortBy(Object.values(belowItems), 'y')
}

function startResize(e: MouseEvent, point: string, item: CanvasItem, index: number) {
  if (!resizable.value) return
  dashboardStore.setCurComponent(item)
  props.resizeStart(e, item, index)

  // Obtain the target element
  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }
  infoBox.value.resizeItem = item
  infoBox.value.resizeItemIndex = index
  // Drag and drop coordinate points
  infoBox.value.point = point
}

function containerClick() {
  // remove current component info
  dashboardStore.setCurComponent(null)
}

function containerMouseDown(e: MouseEvent) {
  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }
  infoBox.value.startX = e.pageX
  infoBox.value.startY = e.pageY
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  if (isMainCanvas(props.canvasId) && curComponent.value?.editing) {
    // do SQtext
  } else {
    e.preventDefault()
    e.stopPropagation()
  }
}

function getNowPosition(addSizeX: number, addSizeY: number, moveXSize: number, moveYSize: number) {
  const point = infoBox.value.point
  const hasT = /t/.test(point)
  const hasB = /b/.test(point)
  const hasL = /l/.test(point)
  const hasR = /r/.test(point)
  // Determine the resizing direction based on the coordinate points
  let nowSizeX = infoBox.value.oldSizeX
  let nowSizeY = infoBox.value.oldSizeY
  let nowX = infoBox.value.oldX
  let nowY = infoBox.value.oldY

  let nowOriginWidth = infoBox.value.originWidth
  let nowOriginHeight = infoBox.value.originHeight
  let nowOriginX = infoBox.value.originX
  let nowOriginY = infoBox.value.originY

  // Move the lowest position from point T
  const nowBottomOriginY = nowOriginY + nowOriginHeight - baseHeight.value
  // Move the lowest position from point L
  const nowLeftOrigin = nowOriginX + nowOriginWidth - baseWidth.value
  const nowBottomX = nowX + nowSizeX - 1
  if (hasR) {
    nowSizeX = Math.max(nowSizeX + addSizeX, 1)
    nowOriginWidth = Math.max(nowOriginWidth + moveXSize, baseWidth.value)
  }
  if (hasB) {
    nowSizeY = Math.max(nowSizeY + addSizeY, 1)
    nowOriginHeight = Math.max(nowOriginHeight + moveYSize, baseHeight.value)
  }

  if (hasL) {
    // Do not exceed the left boundary
    nowSizeX = Math.min(Math.max(nowSizeX - addSizeX, 1), nowBottomX)
    // Move the lowest position from point L
    nowX = Math.min(Math.max(nowX + addSizeX, 1), nowBottomX)

    nowOriginWidth = Math.min(Math.max(nowOriginWidth - moveXSize, baseWidth.value), nowLeftOrigin)
    // Move the lowest position from point L
    nowOriginX = Math.min(Math.max(nowOriginX + moveXSize, 1), nowLeftOrigin)
  }

  if (hasT) {
    nowSizeY = Math.max(nowSizeY - addSizeY, 1)
    nowY = Math.max(nowY + addSizeY, 1)
    nowOriginHeight = Math.max(nowOriginHeight - moveYSize, baseHeight.value)
    // Move the lowest position from point L
    nowOriginY = Math.min(Math.max(nowOriginY + moveYSize, 1), nowBottomOriginY)
  }
  return { nowSizeX, nowSizeY, nowX, nowY, nowOriginWidth, nowOriginHeight, nowOriginX, nowOriginY }
}

function checkStartMove() {
  const cloneItem = infoBox.value.cloneItem
  const nowItemNode = infoBox.value.nowItemNode
  const offsetX = cellWidth.value * 2
  const offsetY = cellHeight.value * 2
  if (cloneItem && nowItemNode) {
    const xGap = Math.abs(cloneItem.offsetLeft - nowItemNode.offsetLeft)
    const yGap = Math.abs(cloneItem.offsetTop - nowItemNode.offsetTop)
    return {
      xMove: xGap > offsetX,
      yMove: yGap > offsetY,
    }
  }
  return {
    xMove: false,
    yMove: false,
  }
}

function startMove(e: MouseEvent, item: CanvasItem, index: number) {
  canvasLocked.value = false // Reset canvas lock status
  if (!draggable.value) return
  dashboardStore.setCurComponent(item)
  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }

  const target = e.target
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  let className = target.className || ''

  if (
    !className.includes('dragHandle') &&
    !className.includes('item') &&
    !className.includes('resizeHandle')
  ) {
    return
  }

  if (className.includes('resizeHandle')) {
    // Handle resize (optional)
  } else if (draggable.value && (className.includes('dragHandle') || className.includes('item'))) {
    props.dragStart(e, item, index)
    infoBox.value.moveItem = item
    infoBox.value.moveItemIndex = index
  }
  infoBox.value.cloneItem = null
  infoBox.value.nowItemNode = null
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  if (target.className.includes('item')) {
    infoBox.value.nowItemNode = target
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    infoBox.value.cloneItem = target.cloneNode(true)
  } else {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    infoBox.value.nowItemNode = target.closest('.item')
    infoBox.value.cloneItem = infoBox.value.nowItemNode.cloneNode(true)
  }
  infoBox.value.cloneItem.classList.add('cloneNode')
  const img = new Image()
  img.classList.add('clone_img')
  const clonedSlot = infoBox.value.nowItemNode.querySelector('.slot-component')

  html2canvas(clonedSlot).then((canvas) => {
    img.src = canvas.toDataURL()
    infoBox.value.cloneItem?.appendChild(img)
  })

  if (containerRef.value) {
    containerRef.value.append(infoBox.value.cloneItem)
  }

  infoBox.value.originX = infoBox.value.cloneItem.offsetLeft
  infoBox.value.originY = infoBox.value.cloneItem.offsetTop
  infoBox.value.oldX = item.x
  infoBox.value.oldY = item.y
  infoBox.value.oldSizeX = item.sizeX
  infoBox.value.oldSizeY = item.sizeY
  infoBox.value.originWidth = infoBox.value.cloneItem.offsetWidth
  infoBox.value.originHeight = infoBox.value.cloneItem.offsetHeight
  const itemMouseMove = (e: MouseEvent) => {
    const moveItem = _.get(infoBox.value, 'moveItem')
    const resizeItem = _.get(infoBox.value, 'resizeItem')

    if (resizeItem) {
      props.resizing(e, resizeItem, resizeItem._dragId)
      infoBox.value.resizeItem.isPlayer = true

      const moveXSize = e.pageX - infoBox.value.startX
      const moveYSize = e.pageY - infoBox.value.startY

      const addSizeX =
        moveXSize % cellWidth.value > cellWidth.value / 4
          ? parseInt(String(moveXSize / cellWidth.value + 1))
          : parseInt(String(moveXSize / cellWidth.value))

      const addSizeY =
        moveYSize % cellHeight.value > cellHeight.value / 4
          ? parseInt(String(moveYSize / cellHeight.value + 1))
          : parseInt(String(moveYSize / cellHeight.value))
      // Determine the resizing direction based on the coordinate points
      const {
        nowSizeX,
        nowSizeY,
        nowX,
        nowY,
        nowOriginWidth,
        nowOriginHeight,
        nowOriginX,
        nowOriginY,
      } = getNowPosition(addSizeX, addSizeY, moveXSize, moveYSize)

      debounce(() => {
        resizePlayer(resizeItem, { sizeX: nowSizeX, sizeY: nowSizeY, x: nowX, y: nowY })
      }, 10)

      infoBox.value.cloneItem.style.width = `${nowOriginWidth}px`
      infoBox.value.cloneItem.style.height = `${nowOriginHeight}px`
      infoBox.value.cloneItem.style.left = `${nowOriginX}px`
      infoBox.value.cloneItem.style.top = `${nowOriginY}px`
    } else if (moveItem) {
      scrollScreen(e)
      if (!draggable.value) return

      props.dragging(e, moveItem, moveItem._dragId)
      moveItem.isPlayer = true
      const moveXSize = e.pageX - infoBox.value.startX
      const moveYSize = e.pageY - infoBox.value.startY

      let nowCloneItemX = infoBox.value.originX + moveXSize
      let nowCloneItemY = infoBox.value.originY + moveYSize
      infoBox.value.cloneItem.style.left = `${nowCloneItemX}px`
      infoBox.value.cloneItem.style.top = `${nowCloneItemY}px`
      tabMoveInCheckSQ()
      tabMoveOutCheckSQ()

      //If the current canvas is locked, no component movement will be performed
      if (canvasLocked.value) return
      const { xMove, yMove } = checkStartMove()
      // Adjust the accuracy of moving coordinate changes
      let newX = xMove ? Math.round(nowCloneItemX / cellWidth.value) : infoBox.value.oldX
      let newY = yMove ? Math.round(nowCloneItemY / cellHeight.value) : infoBox.value.oldY
      newX = newX > 0 ? newX : 1
      newY = newY > 0 ? newY : 1
      debounce(() => {
        if (newX !== infoBox.value.oldX || newY !== infoBox.value.oldY) {
          movePlayer(moveItem, { x: newX, y: newY })
          infoBox.value.oldX = newX
          infoBox.value.oldY = newY
        }
      }, 10)
    }
  }

  window.addEventListener('mousemove', itemMouseMove)

  // Need to execute before mouseup
  const itemCanvasChange = () => {
    // The current canvas movement is in a locked state, indicating that there are components that require canvas switching
    if (canvasLocked.value) {
      const moveItem = infoBox.value.moveItem
      // Get the SQTab currently being moved in
      const curActiveMoveInSQTab = canvasComponentData?.value.find(
        (item) => item.component === 'SQTab' && item.collisionActive === true
      )
      if (curActiveMoveInSQTab) {
        if (curActiveMoveInSQTab.moveInActive) {
          const refTabInstance =
            currentInstance.refs['shape_component_' + curActiveMoveInSQTab.id][0]
          refTabInstance.addTabItem(moveItem)
          removeItemById(moveItem.id)
        }
        curActiveMoveInSQTab.collisionActive = false
        curActiveMoveInSQTab.moveInActive = false
      }

      // move out
      if (props.parentConfigItem && props.parentConfigItem.moveOutActive) {
        emits('parentAddItemBox', _.cloneDeep(moveItem))
        removeItemById(moveItem.id)
        // eslint-disable-next-line vue/no-mutating-props
        props.parentConfigItem.moveOutActive = false
      }
    }
    canvasLocked.value = false
  }

  const itemMouseUp = () => {
    if (_.isEmpty(infoBox.value)) return
    if (infoBox.value.cloneItem) {
      infoBox.value.cloneItem.remove()
    }
    if (infoBox.value.resizeItem) {
      delete infoBox.value.resizeItem.isPlayer
      props.resizeEnd(e, infoBox.value.resizeItem, infoBox.value.resizeItem._dragId)

      if (infoBox.value.resizeItem.component === 'SQTab') {
        const refTabInstance =
          currentInstance.refs['shape_component_' + infoBox.value.resizeItem.id][0]
        refTabInstance.outResizeEnd()
      }
    }
    if (infoBox.value.moveItem) {
      props.dragEnd(e, infoBox.value.moveItem, infoBox.value.moveItem._dragId)
      infoBox.value.moveItem.show = true
      delete infoBox.value.moveItem.isPlayer
    }
    itemCanvasChange()
    infoBox.value = {}

    window.removeEventListener('mousemove', itemMouseMove)
    window.removeEventListener('mouseup', itemMouseUp)
  }

  // This will prevent click events from being passed to the parent level
  window.addEventListener('mouseup', itemMouseUp)
}

function nowItemStyle(item: CanvasItem) {
  return {
    width: cellWidth.value * item.sizeX - baseMarginLeft.value + 'px',
    height: cellHeight.value * item.sizeY - baseMarginTop.value + 'px',
    left: cellWidth.value * (item.x - 1) + baseMarginLeft.value + 'px',
    top: cellHeight.value * (item.y - 1) + baseMarginTop.value + 'px',
  }
}

function getList() {
  let returnList = _.sortBy(_.cloneDeep(canvasComponentData.value), 'y')
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  let finalList = []
  _.forEach(returnList, function (item) {
    if (_.isEmpty(item)) return
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    delete item['_dragId']
    delete item['show']
    finalList.push(item)
  })
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  return finalList
}

function getMaxCell() {
  return maxCell.value
}

function getRenderState() {
  return moveAnimate.value
}

// @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
function afterInitOk(func) {
  let timeId = setInterval(() => {
    if (moveAnimate.value) {
      clearInterval(timeId)
      func()
    }
  }, 100)
}

const forceComputed = () => {
  // Force the trigger of copy-add calculation here, as the position calculation uses a method and there is no change in internal style attributes
  // In some cases, recalculation may not be triggered, resulting in a positional offset. The cellHeight property is being monitored, and forced recalculation is performed here
  cellHeight.value = cellHeight.value + 0.001
  nextTick(function () {
    cellHeight.value = cellHeight.value - 0.001
  })
}

function addItemBox(item: CanvasItem) {
  canvasComponentData.value.push(item)
  forceComputed()
  nextTick(() => {
    addItem(item, canvasComponentData.value.length - 1)
  })
}

function endMove() {
  // do endMove
}

function moving() {
  // do moving
}

// Obtain matrix position
function getItemMatrixPosition(item: CanvasItem) {
  return {
    tw: item.sizeX,
    th: item.sizeY,
    tl: item.x - 1,
    tr: item.sizeX + item.x - 1,
    tt: item.y - 1,
    tb: item.sizeY + item.y - 1,
  }
}

// Get style location
function getItemStylePosition(item: CanvasItem) {
  const { tw, th, tl, tr, tt, tb } = getItemMatrixPosition(item)
  return {
    tw: tw * cellWidth.value - baseMarginLeft.value,
    tl: cellWidth.value * tl + baseMarginLeft.value,
    tr: cellWidth.value * tr + baseMarginLeft.value,
    th: th * cellHeight.value - baseMarginTop.value,
    tt: cellHeight.value * tt + baseMarginTop.value,
    tb: cellHeight.value * tb + baseMarginTop.value,
  }
}

function tabMoveOutCheckSQ() {
  const { cloneItem, moveItem } = infoBox.value
  if (cloneItem && moveItem && props.canvasId.includes('tab') && props.parentConfigItem) {
    const left = cloneItem.offsetLeft
    const width = cloneItem.offsetWidth
    const top = cloneItem.offsetTop
    const { tw } = getItemStylePosition(props.parentConfigItem)
    // eslint-disable-next-line vue/no-mutating-props
    props.parentConfigItem.moveOutActive =
      left < -tabMoveOutXOffset || top < -tabMoveOutYOffset || left + width - tw > tabMoveOutXOffset
    canvasLocked.value = props.parentConfigItem.moveOutActive
  }
}

function tabMoveInCheckSQ() {
  const { cloneItem, moveItem } = infoBox.value
  if (cloneItem && moveItem && moveItem.component !== 'SQTab') {
    const width = cloneItem.offsetWidth
    const height = cloneItem.offsetHeight
    const left = cloneItem.offsetLeft
    const top = cloneItem.offsetTop
    canvasComponentData.value.forEach((item) => {
      if (item.id !== moveItem.id && item.component === 'SQTab') {
        const { tw, th, tl, tt } = getItemStylePosition(item)
        // Collision effective area inspection
        const collisionT = tt + tabMoveInYOffset
        const collisionL = tl + collisionGap - width
        const collisionW = tw + 2 * width - collisionGap
        const collisionH = th + height - tabMoveInYOffset
        // Near the upper left corner area
        const tfAndTf = collisionT <= top && collisionL <= left
        // Near the lower left corner area
        const bfAndBf = collisionT + collisionH >= top + height && collisionL <= left
        // Near the upper right corner area
        const trAndTr = collisionT <= top && collisionL + collisionW >= left + width
        // Near the lower right corner area
        const brAndBr =
          collisionT + collisionH >= top + height && collisionL + collisionW >= left + width
        item.collisionActive = tfAndTf && bfAndBf && trAndTr && brAndBr
        canvasLocked.value = item.collisionActive // Contains collision move in operation, locking canvas

        //Move into effective area for inspection
        //Collision effective area inspection
        const activeT = tt + tabMoveInYOffset
        const activeL = tl + collisionGap * 10 - width
        const activeW = tw + 2 * width - collisionGap * 20
        const activeH = th + height - 2 * tabMoveInYOffset

        // Near the upper left corner area
        const activeTfAndTf = activeT <= top && activeL <= left
        // Near the lower left corner area
        const activeBfAndBf = activeT + activeH >= top + height && activeL <= left
        // Near the upper right corner area
        const activeTrAndTr = activeT <= top && activeL + activeW >= left + width
        // Near the lower right corner area
        const activeBrAndBr = activeT + activeH >= top + height && activeL + activeW >= left + width

        item.moveInActive = activeTfAndTf && activeBfAndBf && activeTrAndTr && activeBrAndBr
      }
    })
  }
}

/**
 * Find position box
 */
function findPositionX(width: number) {
  let resultX = 1
  let checkPointYIndex = -1 // -1 means not occupying any Y-direction canvas
  // Component width
  let pb = positionBox.value
  if (width <= 0) return
  // Find the highest position index of the component. Component rule: the latest y is 1.
  canvasComponentData.value.forEach((component) => {
    const componentYIndex = component.y + component.sizeY - 2
    if (checkPointYIndex < componentYIndex) {
      checkPointYIndex = componentYIndex
    }
  })
  // Start checking from index i in the X direction;
  const pbX = pb[checkPointYIndex]
  // Get the last column array in the X direction
  if (checkPointYIndex < 0 || !pbX) {
    return 1
  } else {
    // The width to check is the component width. The end index of the check is checkEndIndex = i + width - 1;
    // The exit condition for the check is when the end index checkEndIndex is out of bounds (exceeds the end index of pbX).
    for (let i = 0, checkEndIndex = width - 1; checkEndIndex < pbX.length; i++, checkEndIndex++) {
      let adaptorCount = 0
      // Locate the occupied position in the last column
      for (let k = 0; k < width; k++) {
        // pbX[i + k].el === false indicates that the current matrix point is not occupied. When the width of consecutive unoccupied matrix points equals the component width, the starting point i is available.
        if (!pbX[i + k].el) {
          adaptorCount++
        }
      }
      if (adaptorCount === width) {
        resultX = i + 1
        break
      }
    }
    return resultX
  }
}

useEmitt({
  name: `editor-delete-${props.canvasId}`,
  callback: removeItemById,
})

onMounted(() => {
  currentInstance = getCurrentInstance()
})

const enlargeView = (itemId: string) => {
  const refTabInstance = currentInstance.refs['shape_component_' + itemId][0]
  refTabInstance.enlargeView()
}

defineExpose({
  getRenderState,
  init,
  sizeInit,
  afterInitOk,
  addItemBox,
  getMaxCell,
  getList,
  startMove,
  containerMouseDown,
  changeToCoord,
  removeItem,
  findClosetCoords,
  makeCoordinate,
  findPositionX,
})
</script>

<template>
  <div
    ref="containerRef"
    class="dragAndResize"
    @click="containerClick"
    @mousedown="containerMouseDown($event)"
    @mouseup="endMove()"
    @mousemove="moving()"
  >
    <EmptyBackground
      v-if="!canvasComponentData.length && isMainCanvas(canvasId)"
      :description="t('dashboard.add_component_tips')"
    />
    <template v-if="renderOk">
      <CanvasShape
        v-for="(item, index) in canvasComponentData"
        :key="'item' + index"
        :can-edit="!fullscreenFlag"
        :active="curComponentId === item.id"
        :config-item="item"
        :draggable="draggable"
        :item-index="index"
        :move-animate="moveAnimate"
        :start-move="startMove"
        :start-resize="startResize"
        :canvas-id="canvasId"
        :style="nowItemStyle(item)"
        @enlarge-view="() => enlargeView(item.id)"
      >
        <component
          :is="findComponent(item.component)"
          :ref="'shape_component_' + item.id"
          class="sq-component slot-component"
          :class="{ 'sq-component-hidden': item.component !== 'SQTab' }"
          :config-item="item"
          :view-info="canvasViewInfo[item.id]"
          :canvas-view-info="canvasViewInfo"
          :show-position="'canvas'"
          @parent-add-item-box="(subItem: any) => addItemBox(subItem)"
        >
        </component>
      </CanvasShape>
    </template>
  </div>
</template>

<style scoped lang="less">
@import '../css/CanvasStyle.less';
</style>
