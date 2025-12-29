<script lang="ts" setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import { datasourceApi } from '@/api/datasource'
import { useI18n } from 'vue-i18n'
import { Graph, Cell, Shape } from '@antv/x6'
import type { AnyColumn } from 'element-plus-secondary/es/components/table-v2/src/common.mjs'
import { debounce } from 'lodash-es'

const LINE_HEIGHT = 36
const NODE_WIDTH = 180

const props = withDefaults(
  defineProps<{
    id: number
    dragging: boolean
  }>(),
  {
    id: 0,
    dragging: false,
  }
)

const emits = defineEmits(['getTableName'])

const { t } = useI18n()
const loading = ref(false)
const tooltipY = ref('-999px')
const tooltipX = ref('-999px')
const tooltipContent = ref('')
const nodeIds = ref<any[]>([])

const cells = ref<Cell[]>([])
const edgeOPtion = {
  tools: [
    {
      name: 'button-remove', // 工具名称
      args: { x: 20, y: 20 }, // 工具对应的参数
    },
  ],
  attrs: {
    line: {
      stroke: '#DEE0E3',
      strokeWidth: 2,
    },
  },
}
let graph: any

const resetTooltip = () => {
  tooltipY.value = '-1000px'
  tooltipX.value = '-1000px'
  tooltipContent.value = ''
}

const initGraph = () => {
  Graph.registerPortLayout(
    'erPortPosition',
    (portsPositionArgs) => {
      return portsPositionArgs.map((_, index) => {
        return {
          position: {
            x: 0,
            y: (index + 1) * LINE_HEIGHT + 15,
          },
          angle: 0,
        }
      })
    },
    true
  )

  Graph.registerNode(
    'er-rect',
    {
      inherit: 'rect',
      markup: [
        {
          tagName: 'path',
          selector: 'top',
        },
        {
          tagName: 'rect',
          selector: 'body',
        },
        {
          tagName: 'text',
          selector: 'label',
        },
        {
          tagName: 'path',
          selector: 'div',
        },
      ],
      attrs: {
        top: {
          fill: '#BBBFC4',
          refX: 0,
          refY: 0,
          d: 'M0 5C0 2.23858 2.23858 0 5 0H175C177.761 0 180 2.23858 180 5H0Z',
        },
        rect: {
          strokeWidth: 0.5,
          stroke: '#DEE0E3',
          fill: '#F5F6F7',
          refY: 5,
        },
        div: {
          fillRule: 'evenodd',
          clipRule: 'evenodd',
          fill: '#646A73',
          refX: 12,
          refY: 21,
          fontSize: 14,
          d: 'M1.4773 1.47724C1.67618 1.27836 1.94592 1.16663 2.22719 1.16663H11.7729C12.0541 1.16663 12.3239 1.27836 12.5227 1.47724C12.7216 1.67612 12.8334 1.94586 12.8334 2.22713V11.7728C12.8334 12.0541 12.7216 12.3238 12.5227 12.5227C12.3239 12.7216 12.0541 12.8333 11.7729 12.8333H2.22719C1.64152 12.8333 1.16669 12.3585 1.16669 11.7728V2.22713C1.16669 1.94586 1.27842 1.67612 1.4773 1.47724ZM2.33335 5.83329V8.16662H4.66669V5.83329H2.33335ZM2.33335 9.33329V11.6666H4.66669V9.33329H2.33335ZM5.83335 11.6666H8.16669V9.33329H5.83335V11.6666ZM9.33335 11.6666H11.6667V9.33329H9.33335V11.6666ZM11.6667 8.16662V5.83329H9.33335V8.16662H11.6667ZM8.16669 5.83329H5.83335V8.16662H8.16669V5.83329ZM11.6667 2.33329H2.33335V4.66663H11.6667V2.33329Z',
        },
        label: {
          fill: '#1F2329',
          fontSize: 14,
        },
      },
      ports: {
        groups: {
          list: {
            markup: [
              {
                tagName: 'rect',
                selector: 'portBody',
              },
              {
                tagName: 'text',
                selector: 'portNameLabel',
              },
            ],
            attrs: {
              portBody: {
                width: NODE_WIDTH,
                height: LINE_HEIGHT,
                stroke: '#DEE0E3',
                strokeWidth: 0.5,
                fill: '#ffffff',
                magnet: true,
              },
              portNameLabel: {
                ref: 'portBody',
                refX: 12,
                refY: 9.5,
                fontSize: 14,
                textAnchor: 'left',
                textWrap: {
                  width: 150,
                  height: 24,
                  ellipsis: true,
                },
              },
            },
            position: 'erPortPosition',
          },
        },
      },
    },
    true
  )
  graph = new Graph({
    mousewheel: {
      enabled: true,
      modifiers: ['ctrl', 'meta'],
      factor: 1.05,
    },
    container: document.getElementById('container')!,
    autoResize: true,
    panning: true,
    connecting: {
      allowBlank: false,
      router: {
        name: 'er',
        args: {
          offset: 25,
          direction: 'H',
        },
      },
      validateEdge({ edge }: any) {
        const obj = edge.store.data
        if (!obj.target.port || obj.target.cell === obj.source.cell) return false
        return true
      },
      createEdge() {
        return new Shape.Edge(edgeOPtion)
      },
    },
  })

  graph.on('edge:mouseenter', ({ e }: any) => {
    Array.from(document.querySelectorAll('.x6-edge-tool')).forEach((ele: any) => {
      if (ele.dataset.cellId === e.target.parentNode.dataset.cellId) {
        ele.style.display = 'block'
      }
    })
  })

  graph.on('edge:mouseleave', ({ e }: any) => {
    Array.from(document.querySelectorAll('.x6-edge-tool')).forEach((ele: any) => {
      if (ele.dataset.cellId === e.target.parentNode.dataset.cellId) {
        ele.style.display = 'none'
      }
    })
  })

  graph.on(
    'node:port:mouseenter',
    debounce(({ e, node, port }: any) => {
      tooltipY.value = e.offsetY + 'px'
      tooltipX.value = e.offsetX + 'px'
      tooltipContent.value = node.port.ports.find(
        (ele: any) => +port === ele.id
      ).attrs.portNameLabel.text
    }, 100)
  )

  graph.on(
    'cell:mouseover',
    debounce(({ e, cell }: any) => {
      if (cell.store.data.shape === 'edge') return
      tooltipY.value = e.offsetY + 'px'
      tooltipX.value = e.offsetX + 'px'
      tooltipContent.value = cell.store.data.attrs?.label?.text
    }, 100)
  )

  graph.on(
    'node:mouseleave',
    debounce(() => {
      resetTooltip()
    }, 100)
  )

  graph.on('node:mouseenter', ({ node }: any) => {
    node.addTools({
      name: 'button',
      args: {
        markup: [
          {
            tagName: 'circle',
            selector: 'button',
            attrs: {
              r: 7,
              cursor: 'pointer',
            },
          },
          {
            tagName: 'path',
            selector: 'icon',
            attrs: {
              d: 'M -3 -3 3 3 M -3 3 3 -3',
              stroke: 'white',
              'stroke-width': 2,
              cursor: 'pointer',
            },
          },
        ],
        x: 0,
        y: 0,
        offset: { x: 165, y: 28 },
        onClick({ view }: any) {
          node.removeTools()
          graph.removeNode(view.cell.id)
          nodeIds.value = nodeIds.value.filter((ele) => ele !== view.cell.id)
          resetTooltip()
          if (!nodeIds.value.length) {
            graph.dispose()
            graph = null
          }
          emits('getTableName', [...nodeIds.value])
        },
      },
    })
  })

  // 鼠标移开时删除按钮
  graph.on('node:mouseleave', ({ node }: any) => {
    node.removeTools() // 删除所有的工具
  })
}

const getTableData = () => {
  loading.value = true
  datasourceApi
    .relationGet(props.id)
    .then((data: any) => {
      if (!data.length) return
      nodeIds.value = data.filter((ele: any) => ele.shape === 'er-rect').map((ele: any) => ele.id)
      nextTick(() => {
        if (!graph) {
          initGraph()
        }
        data.forEach((item: any) => {
          if (item.shape === 'edge') {
            cells.value.push(graph.createEdge({ ...item, ...edgeOPtion }))
          } else {
            cells.value.push(
              graph.createNode({
                ...item,
                height: LINE_HEIGHT + 15,
                width: NODE_WIDTH,
              })
            )
          }
        })
        graph.resetCells(cells.value)
        graph.zoomToFit({ padding: 100 })
        emits('getTableName', [...nodeIds.value])
      })
    })
    .finally(() => {
      loading.value = false
    })
}
onMounted(() => {
  getTableData()
})
onBeforeUnmount(() => {
  graph = null
})
const dragover = () => {
  // do
}

const addNode = (node: any, tableX: any, tableY: any) => {
  if (!graph) {
    initGraph()
  }
  const { x, y } = graph.pageToLocal(tableX, tableY)
  graph.addNode(
    graph.createNode({
      ...node,
      position: {
        x,
        y,
      },
      attrs: {
        label: {
          text: node.label,
          textAnchor: 'left',
          refX: 34,
          refY: 28,
          textWrap: {
            width: 120,
            height: 24,
            ellipsis: true,
          },
        },
      },
      height: LINE_HEIGHT + 15,
      width: NODE_WIDTH,
    })
  )
}

const clickTable = (table: any) => {
  loading.value = true
  datasourceApi
    .fieldList(table.id)
    .then((res: AnyColumn) => {
      const node = {
        id: table.id,
        shape: 'er-rect',
        label: table.table_name,
        width: 150,
        height: 24,
        ports: res.map((ele: any) => {
          return {
            id: ele.id,
            group: 'list',
            attrs: {
              portNameLabel: {
                text: ele.field_name,
              },
              portTypeLabel: {
                text: ele.field_type,
              },
            },
          }
        }),
      }
      nodeIds.value = [...nodeIds.value, table.id]
      nextTick(() => {
        addNode(node, table.x, table.y)
      })
      emits('getTableName', [...nodeIds.value])
    })
    .finally(() => {
      loading.value = false
    })
}

const drop = (e: any) => {
  const obj = JSON.parse(e.dataTransfer.getData('table') || '{}')
  if (!obj.id) return
  clickTable({
    ...obj,
    x: e.pageX,
    y: e.pageY,
  })
}
const save = () => {
  datasourceApi.relationSave(props.id, graph.toJSON().cells).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
  })
}
</script>

<template>
  <svg style="position: fixed; top: -9999px" xmlns:xlink="http://www.w3.org/1999/xlink">
    <defs>
      <filter
        x="-1"
        y="-1"
        width="3"
        height="3"
        filterUnits="objectBoundingBox"
        id="filter-dropShadow-v0-3329848037"
      >
        <feDropShadow
          stdDeviation="4"
          dx="1"
          dy="2"
          flood-color="#1F23291F"
          flood-opacity="0.65"
        ></feDropShadow>
      </filter>
    </defs>
  </svg>
  <div v-loading="loading" v-if="!nodeIds.length" class="relationship-empty">
    {{ t('training.add_it_here') }}
  </div>
  <div v-loading="loading" v-else id="container"></div>
  <div
    @dragover.prevent.stop="dragover"
    @drop.prevent.stop="drop"
    v-show="dragging"
    class="drag-mask"
  ></div>
  <div class="save-btn">
    <el-button type="primary" v-if="nodeIds.length" @click="save">
      {{ t('common.save') }}
    </el-button>
  </div>
  <div class="tooltip-content" :style="{ top: tooltipY, left: tooltipX, position: 'absolute' }">
    {{ tooltipContent }}
  </div>
</template>

<style lang="less" scoped>
.tooltip-content {
  font-weight: 400;
  direction: ltr;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  outline: none;
  border-radius: 4px;
  padding: 5px 11px;
  font-size: 12px;
  line-height: 20px;
  min-width: 10px;
  overflow-wrap: break-word;
  word-break: normal;
  visibility: visible;
  color: #fff;
  background: #303133;
  border: 1px solid #303133;
  transform: translate(20px, -15px);
}
.save-btn {
  position: absolute;
  right: 16px;
  bottom: 16px;
}
.drag-mask {
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 56px;
  z-index: 10;
}
.relationship-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 16px;
}
#container {
  font-size: 14px;
  user-select: text;
  overflow: hidden;
  outline: none;
  touch-action: none;
  box-sizing: border-box;
  position: relative;
  min-width: 400px;
  min-height: 600px;
  width: 100%;
  height: 100%;
  background-color: #f5f6f7;
  :deep(.x6-edge-tool) {
    display: none;

    circle {
      fill: var(--ed-color-primary) !important;
    }
  }

  :deep(.x6-node-tool) {
    circle {
      fill: var(--ed-color-primary) !important;
    }
  }

  :deep(.x6-node) {
    filter: url(#filter-dropShadow-v0-3329848037);
  }
}
</style>
