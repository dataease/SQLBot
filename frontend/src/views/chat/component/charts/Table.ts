import { BaseChart, type ChartAxis, type ChartData } from '@/views/chat/component/BaseChart.ts'
import {
  TableSheet,
  S2Event,
  copyToClipboard,
  type S2Options,
  type S2DataConfig,
  type S2MountContainer,
  type SortMethod,
  type Node,
  type CellTextWordWrapStyle,
} from '@antv/s2'
import { debounce, filter } from 'lodash-es'
import { i18n } from '@/i18n'

const { t } = i18n.global

export class Table extends BaseChart {
  table?: TableSheet = undefined

  container: S2MountContainer | null = null

  debounceRender: any

  resizeObserver: ResizeObserver

  constructor(id: string) {
    super(id, 'table')
    this.container = document.getElementById(id)

    this.debounceRender = debounce(async (width?: number, height?: number) => {
      if (this.table) {
        this.table.changeSheetSize(width, height)
        await this.table.render(false)
      }
    }, 200)

    this.resizeObserver = new ResizeObserver(([entry] = []) => {
      const [size] = entry.borderBoxSize || []
      this.debounceRender(size.inlineSize, size.blockSize)
    })

    if (this.container?.parentElement) {
      this.resizeObserver.observe(this.container.parentElement)
    }
  }

  init(axis: Array<ChartAxis>, data: Array<ChartData>) {
    super.init(
      filter(axis, (a) => !a.hidden), //隐藏多指标的other-info列
      data
    )

    const s2DataConfig: S2DataConfig = {
      sortParams:
        this.axis?.map((a) => {
          return {
            sortFieldId: a.value,
          }
        }) ?? [],
      fields: {
        columns: this.axis?.map((a) => a.value) ?? [],
      },
      meta:
        this.axis?.map((a) => {
          return {
            field: a.value,
            name: a.name,
          }
        }) ?? [],
      data: this.data,
    }

    const cellTextWordWrapStyle: CellTextWordWrapStyle = {
      // 最大行数，文本超出后将被截断
      maxLines: 3,
      // 文本是否换行
      wordWrap: true,
      // 可选项见：https://g.antv.antgroup.com/api/basic/text#textoverflow
      textOverflow: 'ellipsis',
    }

    const s2Options: S2Options = {
      width: 600,
      height: 360,
      showDefaultHeaderActionIcon: true,
      tooltip: {
        enable: true,
        operation: {
          // 开启组内排序
          sort: true,
        },
        colCell: {
          content: (cell) => {
            const meta = cell.getMeta()
            const { spreadsheet: s2 } = meta

            if (!meta.isLeaf) {
              return null
            }

            // 创建类似Element Plus下拉菜单的结构
            const container = document.createElement('div')
            container.className = 'el-dropdown'
            container.style.padding = '8px 0'
            container.style.minWidth = '100px'

            const menuItems = [
              { label: '降序', method: 'desc' as SortMethod, icon: 'el-icon-sort-down' },
              { label: '升序', method: 'asc' as SortMethod, icon: 'el-icon-sort-up' },
              { label: '不排序', method: 'none' as SortMethod, icon: 'el-icon-close' },
            ]

            menuItems.forEach((item) => {
              const itemEl = document.createElement('div')
              itemEl.className = 'el-dropdown-menu__item'
              itemEl.style.display = 'flex'
              itemEl.style.alignItems = 'center'
              itemEl.style.padding = '8px 16px'
              itemEl.style.cursor = 'pointer'
              itemEl.style.color = '#606266'
              itemEl.style.fontSize = '14px'

              // 鼠标悬停效果
              itemEl.addEventListener('mouseenter', () => {
                itemEl.style.backgroundColor = '#f5f7fa'
                itemEl.style.color = '#409eff'
              })
              itemEl.addEventListener('mouseleave', () => {
                itemEl.style.backgroundColor = 'transparent'
                itemEl.style.color = '#606266'
              })

              // 添加图标（如果需要）
              if (item.icon) {
                const icon = document.createElement('i')
                icon.className = item.icon
                icon.style.marginRight = '8px'
                icon.style.fontSize = '16px'
                itemEl.appendChild(icon)
              }

              const text = document.createTextNode(item.label)
              itemEl.appendChild(text)

              itemEl.addEventListener('click', (e) => {
                e.stopPropagation()
                s2.groupSortByMethod(item.method, meta as Node)
                // 可以在这里添加关闭tooltip的逻辑
              })

              container.appendChild(itemEl)
            })

            return container
          },
        },
      },
      // 如果有省略号, 复制到的是完整文本
      interaction: {
        copy: {
          enable: true,
          withFormat: true,
          withHeader: true,
        },
        brushSelection: {
          dataCell: true,
          rowCell: true,
          colCell: true,
        },
      },
      style: {
        colCell: cellTextWordWrapStyle,
        // 如果是数值不建议换行, 容易产生歧义
        dataCell: cellTextWordWrapStyle,
      },
      placeholder: {
        cell: '-',
        empty: {
          icon: 'Empty',
          description: 'No Data',
        },
      },
    }

    if (this.container) {
      this.table = new TableSheet(this.container, s2DataConfig, s2Options)
      console.log(this.table)
      // right click
      this.table.on(S2Event.GLOBAL_COPIED, (data) => {
        ElMessage.success(t('qa.copied'))
        console.debug('copied: ', data)
      })
      this.table.getCanvasElement().addEventListener('contextmenu', (event) => {
        event.preventDefault()
      })
      this.table.on(S2Event.GLOBAL_CONTEXT_MENU, (event) => copyData(event, this.table))
      // this.table.on(S2Event.RANGE_SORT, (sortParams) => {
      //   console.log('sortParams:', sortParams)
      // })
    }
  }

  render() {
    this.table?.render()
  }

  destroy() {
    this.table?.destroy()
    this.resizeObserver?.disconnect()
  }
}

function copyData(event: any, s2?: TableSheet) {
  event.preventDefault()
  if (!s2) {
    return
  }
  const cells = s2.interaction.getCells()

  if (cells.length == 0) {
    return
  } else if (cells.length == 1) {
    const c = cells[0]
    const cellMeta = s2.facet.getCellMeta(c.rowIndex, c.colIndex)
    if (cellMeta) {
      let value = cellMeta.fieldValue
      if (value === null || value === undefined) {
        value = '-'
      }
      value = value + ''
      copyToClipboard(value).finally(() => {
        ElMessage.success(t('qa.copied'))
        console.debug('copied:', cellMeta.fieldValue)
      })
    }
    return
  } else {
    let currentRowIndex = -1
    let currentRowData: Array<string> = []
    const rowData: Array<string> = []
    for (let i = 0; i < cells.length; i++) {
      const c = cells[i]
      const cellMeta = s2.facet.getCellMeta(c.rowIndex, c.colIndex)
      if (!cellMeta) {
        continue
      }
      if (currentRowIndex == -1) {
        currentRowIndex = c.rowIndex
      }
      if (c.rowIndex !== currentRowIndex) {
        rowData.push(currentRowData.join('\t'))
        currentRowData = []
        currentRowIndex = c.rowIndex
      }
      let value = cellMeta.fieldValue
      if (value === null || value === undefined) {
        value = '-'
      }
      value = value + ''
      currentRowData.push(value)
    }
    rowData.push(currentRowData.join('\t'))
    const finalValue = rowData.join('\n')
    copyToClipboard(finalValue).finally(() => {
      ElMessage.success(t('qa.copied'))
      console.debug('copied:\n', finalValue)
    })
  }
}
