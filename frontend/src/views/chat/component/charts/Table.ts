import { BaseChart, type ChartAxis, type ChartData } from '@/views/chat/component/BaseChart.ts'
import {
  TableSheet,
  S2Event,
  copyToClipboard,
  type S2Options,
  type S2DataConfig,
  type S2MountContainer,
} from '@antv/s2'
import { debounce } from 'lodash-es'
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
    super.init(axis, data)

    const s2DataConfig: S2DataConfig = {
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

    const s2Options: S2Options = {
      width: 600,
      height: 360,
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
      // right click
      this.table.on(S2Event.GLOBAL_COPIED, (data) => {
        ElMessage.success(t('qa.copied'))
        console.debug('copied: ', data)
      })
      this.table.getCanvasElement().addEventListener('contextmenu', (event) => {
        event.preventDefault()
      })
      this.table.on(S2Event.GLOBAL_CONTEXT_MENU, (event) => copyData(event, this.table))
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
