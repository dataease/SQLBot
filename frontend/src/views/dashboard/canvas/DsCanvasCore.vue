<script setup lang="ts">
import { ref, nextTick, toRefs } from 'vue'
import _ from 'lodash'
// Props
const props = defineProps({
  canvasComponentData: {
    type: Array,
    required: true
  },
  baseWidth: {
    type: Number,
    default: 100
  },
  baseHeight: {
    type: Number,
    default: 50
  },
  baseMarginLeft: {
    type: Number,
    default: 20
  },
  baseMarginTop: {
    type: Number,
    default: 20
  },
  draggable: {
    type: Boolean,
    default: true
  },
  dragStart: {
    type: Function,
    default: () => {
      return {}
    }
  },
  dragging: {
    type: Function,
    default: () => {
      return {}
    }
  },
  dragEnd: {
    type: Function,
    default: () => {
      return {}
    }
  },
  resizable: {
    type: Boolean,
    default: true
  },
  resizeStart: {
    type: Function,
    default: () => {
      return {}
    }
  },
  resizing: {
    type: Function,
    default: () => {
      return {}
    }
  },
  resizeEnd: {
    type: Function,
    default: () => {
      return {}
    }
  }
})

const {
  canvasComponentData,
  baseWidth,
  baseHeight,
  baseMarginLeft,
  baseMarginTop,
  draggable,
  resizable
} = toRefs(props)

// DOM ref
const containerRef = ref(null)
const renderOk = ref(false)
const moveAnimate = ref(false)
const cellWidth = ref(0)
const cellHeight = ref(0)
const maxCell = ref(0)
const positionBox = ref([])
const coordinates = ref([])
const infoBox = ref()

// Position data (non-reactive)

let lastTask = undefined
let isOverlay = false
let itemMaxX = 0
let itemMaxY = 0

const moveTime = 80
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
 * @param {any} item
 */
function addItemToPositionBox(item: any) {
  const pb = positionBox.value
  if (item.x <= 0 || item.y <= 0) return
  // Traverse the grid at the target location and add the item to it
  for (let i = item.x - 1; i < item.x - 1 + item.sizex; i++) {
    for (let j = item.y - 1; j < item.y - 1 + item.sizey; j++) {
      if (pb[j] && pb[j][i]) {
        // Ensure the target location is valid
        pb[j][i].el = item // Place the item in the corresponding position
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
 * @param {any} item: The item to be removed
 */
function removeItemFromPositionBox(item: any) {
  const pb = positionBox.value
  if (item.x <= 0 || item.y <= 0) return
  // Traverse the area occupied by the item and remove it
  for (let i = item.x - 1; i < item.x - 1 + item.sizex; i++) {
    for (let j = item.y - 1; j < item.y - 1 + item.sizey; j++) {
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
  maxCell.value = Math.round(containerRef.value.offsetWidth / cellWidth.value)
}

function init() {
  cellWidth.value = baseWidth.value + baseMarginLeft.value
  cellHeight.value = baseHeight.value + baseMarginTop.value

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

function resizePlayer(item: any, newSize: any) {
  removeItemFromPositionBox(item)
  const belowItems = findBelowItems(item)
  _.forEach(belowItems, upItem => {
    const canGoUpRows = canItemGoUp(upItem)
    if (canGoUpRows > 0) {
      moveItemUp(upItem, canGoUpRows)
    }
  })

  item.sizex = newSize.sizex
  item.sizey = newSize.sizey

  if (item.sizex + item.x - 1 > itemMaxX) {
    item.sizex = itemMaxX - item.x + 1
  }

  if (item.sizey + item.y > itemMaxY) {
    fillPositionBox(item.y + item.sizey)
  }

  emptyTargetCell(item)
  addItemToPositionBox(item)
  changeItemCoord(item)

  const canGoUpRows = canItemGoUp(item)
  if (canGoUpRows > 0) {
    moveItemUp(item, canGoUpRows)
  }
}

/**
 * Check the position of the movement, if it is illegal, it will be automatically modified
 *
 * @param {any} item
 * @param {any} position
 */
function checkItemPosition(item: any, position = {}) {
  position.x = position.x || item.x
  position.y = position.y || item.y

  // Limit minimum coordinates
  if (item.x < 1) item.x = 1
  if (item.y < 1) item.y = 1

  // Limit minimum size
  if (item.sizex < 1) item.sizex = 1
  if (item.sizey < 1) item.sizey = 1

  // Limit maximum width
  if (item.sizex > itemMaxX) item.sizex = itemMaxX

  // Limit the right side to not exceed the boundary
  if (item.x + item.sizex - 1 > itemMaxX) {
    item.x = itemMaxX - item.sizex + 1
    if (item.x < 1) item.x = 1
  }

  // If the height of the item exceeds the current maximum number of rows, fill the position table
  if (item.y + item.sizey > itemMaxY - 1) {
    fillPositionBox(item.y + item.sizey - 1)
  }
}

/**
 * Move the element being dragged
 *
 * @param {any} item
 * @param {any} position
 */
function movePlayer(item: any, position: any) {
  // Remove item location
  removeItemFromPositionBox(item)
  // Find the item below
  let belowItems = findBelowItems(item)
  // Traverse the items below and move them
  belowItems.forEach(upItem => {
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

function removeItem(index: number) {
  const item = canvasComponentData.value[index]
  removeItemFromPositionBox(item)
  const belowItems = findBelowItems(item)
  belowItems.forEach(upItem => {
    const canGoUpRows = canItemGoUp(upItem)
    if (canGoUpRows > 0) {
      moveItemUp(upItem, canGoUpRows)
    }
  })
  canvasComponentData.value.splice(index, 1, {})
}

function addItem(item, index) {
  if (index < 0) {
    index = canvasComponentData.value.length
  }
  item._dragId = index
  checkItemPosition(item, { x: item.x, y: item.y })
  emptyTargetCell(item)
  addItemToPositionBox(item)
  const canGoUpRows = canItemGoUp(item)
  if (canGoUpRows > 0) {
    moveItemUp(item, canGoUpRows)
  }
  // makeCoordinate(item) // If coordinate points need to be generated, untangle the annotations
}

function changeToCoord(left, top, width, height) {
  return {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2
  }
}

/**
 * Detect for collisions and take appropriate measures
 *
 * @param {any} item comparison object
 * @param {any} tCord compares the coordinates of the object
 */
function findClosetCoords(item, tCoord) {
  if (isOverlay) return
  let collisionsItem = []
  coordinates.value.forEach(nowCoord => {
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
        coord: nowCoord
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
    y: collisionsItem[0].coord.el.y
  })

  setTimeout(() => {
    isOverlay = false
  }, 200)
}
/**
 * Generate coordinates
 * @param {any} item: The item object to generate coordinates for
 */
function makeCoordinate(item) {
  let width = cellWidth.value * item.sizex - baseMarginLeft.value
  let height = cellHeight.value * item.sizey - baseMarginTop.value
  let left = cellWidth.value * (item.x - 1) + baseMarginLeft.value
  let top = cellHeight.value * (item.y - 1) + baseMarginTop.value

  let coord = {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2,
    el: item
  }

  coordinates.value.push(coord)
}

/**
 * Change the coordinates of the item
 * @param {any} item: The item object whose coordinates need to be changed
 */
function changeItemCoord(item) {
  let width = cellWidth.value * item.sizex - baseMarginLeft.value
  let height = cellHeight.value * item.sizey - baseMarginTop.value
  let left = cellWidth.value * (item.x - 1) + baseMarginLeft.value
  let top = cellHeight.value * (item.y - 1) + baseMarginTop.value

  let coord = {
    x1: left,
    x2: left + width,
    y1: top,
    y2: top + height,
    c1: left + width / 2,
    c2: top + height / 2,
    el: item
  }

  // Find and update the corresponding coordinates
  const index = coordinates.value.findIndex(o => o.el._dragId === item._dragId)
  if (index !== -1) {
    coordinates.value.splice(index, 1, coord)
  }
}
/**
 * Clear the elements at the target location
 * @param {any} item Target item
 */
function emptyTargetCell(item: any) {
  let belowItems = findBelowItems(item)

  belowItems.forEach(downItem => {
    if (downItem._dragId === item._dragId) return
    let moveSize = item.y + item.sizey - downItem.y
    if (moveSize > 0) {
      moveItemDown(downItem, moveSize)
    }
  })
}

/**
 * Can the item at the current location float up
 * @param {any} item Current item
 */
function canItemGoUp(item) {
  let upperRows = 0
  for (let row = item.y - 2; row >= 0; row--) {
    for (let cell = item.x - 1; cell < item.x - 1 + item.sizex; cell++) {
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
 * @param {any} items
 * @param {any} size
 */
function moveItemDown(item, size) {
  removeItemFromPositionBox(item)

  const belowItems = findBelowItems(item)

  for (const downItem of belowItems) {
    if (downItem._dragId === item._dragId) continue

    const moveSize = calcDiff(item, downItem, size)
    if (moveSize > 0) {
      moveItemDown(downItem, moveSize)
    }
  }

  const targetPosition = {
    y: item.y + size
  }

  setPlayerPosition(item, targetPosition)
  checkItemPosition(item, targetPosition)

  addItemToPositionBox(item)
  changeItemCoord(item)
}

function setPlayerPosition(item, position = {}) {
  const targetX = position.x || item.x
  const targetY = position.y || item.y

  item.x = targetX
  item.y = targetY

  if (item.y + item.sizey > itemMaxY) {
    itemMaxY = item.y + item.sizey
  }
}

/**
 * Find the maximum distance from a child element to its parent element
 *
 * @param {any} parent
 * @param {any} son
 * @param {any} size
 */
function calcDiff(parent, son, size) {
  const diffs = []

  for (let i = son.x - 1; i < son.x - 1 + son.sizex; i++) {
    let temp_y = 0

    for (let j = parent.y - 1 + parent.sizey; j < son.y - 1; j++) {
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

function moveItemUp(item, size) {
  removeItemFromPositionBox(item)

  const belowItems = findBelowItems(item)

  setPlayerPosition(item, {
    y: item.y - size
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

function findBelowItems(item) {
  const belowItems = {}

  for (let cell = item.x - 1; cell < item.x - 1 + item.sizex; cell++) {
    for (let row = item.y - 1; row < positionBox.value.length; row++) {
      const target = positionBox.value[row][cell]
      if (target && target.el) {
        belowItems[target.el._dragId] = target.el
        break
      }
    }
  }

  return _.sortBy(Object.values(belowItems), 'y')
}

function startResize(e, item, index) {
  if (!resizable.value) return
  props.resizeStart(e, item, index)

  // Obtain the target element
  let target = e.target
  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }
  // Get the parent element of. tem
  let itemNode = target.closest('.item')
  infoBox.value.resizeItem = item
  infoBox.value.resizeItemIndex = index
}

function containerMouseDown(e) {
  // e.preventDefault();
  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }
  infoBox.value.startX = e.pageX
  infoBox.value.startY = e.pageY
}

function startMove(e, item, index) {
  if (!draggable.value) return

  if (!infoBox.value) {
    infoBox.value = {} // Reinitialize
  }

  const target = e.target
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

  if (target.className.includes('item')) {
    infoBox.value.nowItemNode = target
    infoBox.value.cloneItem = target.cloneNode(true)
  } else {
    infoBox.value.nowItemNode = target.closest('.item')
    infoBox.value.cloneItem = infoBox.value.nowItemNode.cloneNode(true)
  }

  infoBox.value.cloneItem.classList.add('cloneNode')
  document.body.append(infoBox.value.cloneItem)

  infoBox.value.originX = infoBox.value.cloneItem.offsetLeft
  infoBox.value.originY = infoBox.value.cloneItem.offsetTop
  infoBox.value.oldX = item.x
  infoBox.value.oldY = item.y
  infoBox.value.oldSizeX = item.sizex
  infoBox.value.oldSizeY = item.sizey
  infoBox.value.originWidth = infoBox.value.cloneItem.offsetWidth
  infoBox.value.originHeight = infoBox.value.cloneItem.offsetHeight
  const itemMouseMove = e => {
    const moveItem = _.get(infoBox.value, 'moveItem')
    const resizeItem = _.get(infoBox.value, 'resizeItem')

    if (resizeItem) {
      props.resizing(e, resizeItem, resizeItem._dragId)
      infoBox.value.resizeItem.isPlayer = true

      const moveXSize = e.pageX - infoBox.value.startX
      const moveYSize = e.pageY - infoBox.value.startY

      const addSizex =
        moveXSize % cellWidth.value > (cellWidth.value / 4) * 1
          ? parseInt(moveXSize / cellWidth.value + 1)
          : parseInt(moveXSize / cellWidth.value)

      const addSizey =
        moveYSize % cellHeight.value > (cellHeight.value / 4) * 1
          ? parseInt(moveYSize / cellHeight.value + 1)
          : parseInt(moveYSize / cellHeight.value)

      const nowX = Math.max(infoBox.value.oldSizeX + addSizex, 1)
      const nowY = Math.max(infoBox.value.oldSizeY + addSizey, 1)

      debounce(() => {
        resizePlayer(resizeItem, { sizex: nowX, sizey: nowY })
      }, 10)

      const nowWidth = Math.max(infoBox.value.originWidth + moveXSize, baseWidth.value)
      const nowHeight = Math.max(infoBox.value.originHeight + moveYSize, baseHeight.value)

      infoBox.value.cloneItem.style.width = `${nowWidth}px`
      infoBox.value.cloneItem.style.height = `${nowHeight}px`
    } else if (moveItem) {
      scrollScreen(e)
      if (!draggable.value) return

      props.dragging(e, moveItem, moveItem._dragId)
      moveItem.isPlayer = true

      const moveXSize = e.pageX - infoBox.value.startX
      const moveYSize = e.pageY - infoBox.value.startY

      let nowCloneItemX = infoBox.value.originX + moveXSize
      let nowCloneItemY = infoBox.value.originY + moveYSize

      const newX = Math.max(
        Math.floor(
          (nowCloneItemX + infoBox.value.cloneItem.offsetWidth / 12 - baseMarginLeft.value) /
            cellWidth.value +
            1
        ),
        1
      )

      const newY = Math.max(
        Math.floor(
          (nowCloneItemY + infoBox.value.cloneItem.offsetHeight / 12 - baseMarginTop.value) /
            cellHeight.value +
            1
        ),
        1
      )

      debounce(() => {
        if (newX !== infoBox.value.oldX || newY !== infoBox.value.oldY) {
          movePlayer(moveItem, { x: newX, y: newY })
          infoBox.value.oldX = newX
          infoBox.value.oldY = newY
        }
      }, 10)

      infoBox.value.cloneItem.style.left = `${nowCloneItemX}px`
      infoBox.value.cloneItem.style.top = `${nowCloneItemY}px`
    }
  }

  window.addEventListener('mousemove', itemMouseMove)

  const itemMouseUp = () => {
    if (_.isEmpty(infoBox.value)) return

    if (infoBox.value.cloneItem) {
      infoBox.value.cloneItem.remove()
    }
    if (infoBox.value.resizeItem) {
      delete infoBox.value.resizeItem.isPlayer
      props.resizeEnd(e, infoBox.value.resizeItem, infoBox.value.resizeItem._dragId)
    }
    if (infoBox.value.moveItem) {
      props.dragEnd(e, infoBox.value.moveItem, infoBox.value.moveItem._dragId)
      infoBox.value.moveItem.show = true
      delete infoBox.value.moveItem.isPlayer
    }
    infoBox.value = {}

    window.removeEventListener('mousemove', itemMouseMove)
    window.removeEventListener('mouseup', itemMouseUp)
  }

  window.addEventListener('mouseup', itemMouseUp)
}

function nowItemStyle(item, index) {
  return {
    width: cellWidth.value * item.sizex - baseMarginLeft.value + 'px',
    height: cellHeight.value * item.sizey - baseMarginTop.value + 'px',
    left: cellWidth.value * (item.x - 1) + baseMarginLeft.value + 'px',
    top: cellHeight.value * (item.y - 1) + baseMarginTop.value + 'px'
  }
}

function getList() {
  let returnList = _.sortBy(_.cloneDeep(canvasComponentData.value), 'y')
  let finalList = []
  _.forEach(returnList, function (item, index) {
    if (_.isEmpty(item)) return
    delete item['_dragId']
    delete item['show']
    finalList.push(item)
  })
  return finalList
}

function getMaxCell() {
  return maxCell.value
}

function getRenderState() {
  return moveAnimate.value
}

function afterInitOk(func) {
  let timeId = setInterval(() => {
    if (moveAnimate.value) {
      clearInterval(timeId)
      func()
    }
  }, 100)
}

function addItemBox(item) {
  canvasComponentData.value.push(item)
  nextTick(() => {
    addItem(item, canvasComponentData.value.length - 1)
  })
}

function endMove(e) {
  // do endMove
}

function moving(e) {
  // do moving
}

defineExpose({
  getRenderState,
  init,
  afterInitOk,
  addItemBox,
  getMaxCell,
  getList,
  nowItemStyle,
  startMove,
  containerMouseDown,
  changeToCoord
})
</script>

<template>
  <div
    class="dragAndResize"
    ref="containerRef"
    @mousedown="containerMouseDown($event)"
    @mouseup="endMove($event)"
    @mousemove="moving($event)"
  >
    <div v-if="renderOk">
      <div
        v-for="(item, index) in canvasComponentData"
        :class="{
          item: true,
          moveAnimation: moveAnimate,
          movingItem: item.isPlayer,
          canNotDrag: !draggable
        }"
        @mousedown="startMove($event, item, index)"
        :ref="'item' + index"
        :key="'item' + index"
        :style="nowItemStyle(item, index)"
      >
        <slot :name="'slot' + index">{{ item }}</slot>
        <span
          class="resizeHandle"
          v-show="resizable"
          @mousedown="startResize($event, item, index)"
        ></span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="less">
@import '../css/DeDrag.less';
</style>
