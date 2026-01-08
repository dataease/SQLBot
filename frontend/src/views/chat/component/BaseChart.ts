export interface ChartAxis {
  name: string
  value: string
  type?: 'x' | 'y' | 'series' | 'other-info'
  'multi-quota'?: boolean
}

export interface ChartData {
  [key: string]: any
}

export type ChartTypes = 'table' | 'bar' | 'column' | 'line' | 'pie'

export abstract class BaseChart {
  id: string
  _name: string = 'base-chart'
  axis: Array<ChartAxis> = []
  data: Array<ChartData> = []

  constructor(id: string, name: string) {
    this.id = id
    this._name = name
  }

  init(axis: Array<ChartAxis>, data: Array<ChartData>): void {
    this.axis = axis
    this.data = data
  }

  abstract render(): void

  abstract destroy(): void
}
