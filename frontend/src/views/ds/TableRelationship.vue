<script lang="ts" setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import { datasourceApi } from '@/api/datasource'
import { useI18n } from 'vue-i18n'
import { Graph, Cell, Shape } from '@antv/x6'
import type { AnyColumn } from 'element-plus-secondary/es/components/table-v2/src/common.mjs'

const LINE_HEIGHT = 36
const NODE_WIDTH = 180

const props = withDefaults(
  defineProps<{
    id: string
    dragging: boolean
  }>(),
  {
    id: '',
    dragging: false,
  }
)

const emits = defineEmits(['getTableName'])

const { t } = useI18n()
const loading = ref(false)

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
      strokeWidth: 1,
    },
  },
}
let graph: any

const initGraph = () => {
  Graph.registerPortLayout(
    'erPortPosition',
    (portsPositionArgs) => {
      return portsPositionArgs.map((_, index) => {
        return {
          position: {
            x: 0,
            y: (index + 1) * LINE_HEIGHT,
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
          tagName: 'rect',
          selector: 'body',
        },
        {
          tagName: 'text',
          selector: 'label',
        },
      ],
      attrs: {
        rect: {
          strokeWidth: 1,
          stroke: '#F5F6F7',
          fill: '#F5F6F7',
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
                strokeWidth: 1,
                stroke: '#1F232926',
                fill: '#ffffff',
                magnet: true,
              },
              portNameLabel: {
                ref: 'portBody',
                refX: 12,
                refY: 8,
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
    },
    container: document.getElementById('container')!,
    autoResize: true,
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
        offset: { x: 165, y: 18 },
        onClick({ view }: any) {
          graph.removeNode(view.cell.id)
          nodeIds.value = nodeIds.value.filter((ele) => ele !== view.cell.id)
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
      nodeIds.value = data.filter((ele: any) => ele.shape === 'er-rect').map((ele: any) => ele.id)
      nextTick(() => {
        if (!graph) {
          initGraph()
        }
        data.forEach((item: any) => {
          if (item.shape === 'edge') {
            cells.value.push(graph.createEdge({ ...item, ...edgeOPtion }))
          } else {
            console.log(item)

            cells.value.push(
              graph.createNode({
                ...item,
                attrs: {
                  label: {
                    text: item.attrs.text.text,
                    textAnchor: 'left',
                    refX: 10,
                    textWrap: {
                      width: 140,
                      height: 24,
                      ellipsis: true,
                    },
                  },
                },
                height: LINE_HEIGHT,
                width: NODE_WIDTH,
              })
            )
          }
        })
        graph.resetCells(cells.value)
        graph.zoomToFit({ padding: 10, maxScale: 1 })
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

const addNode = (node: any) => {
  if (!graph) {
    initGraph()
  }
  graph.addNode(graph.createNode({ ...node, height: LINE_HEIGHT, width: NODE_WIDTH }))
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
        position: {
          x: table.x,
          y: table.y,
        },
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
        addNode(node)
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
  clickTable({ ...obj, x: e.layerX, y: e.layerY })
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
</template>

<style lang="less" scoped>
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
}
</style>
