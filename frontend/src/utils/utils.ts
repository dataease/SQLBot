import dayjs from 'dayjs'
import { useCache } from '@/utils/useCache'
import colorFunctions from 'less/lib/less/functions/color.js'
import colorTree from 'less/lib/less/tree/color.js'

const { wsCache } = useCache()
const getCheckDate = (timestamp: any) => {
  if (!timestamp) return false
  const dt = new Date(timestamp)
  if (isNaN(dt.getTime())) return false
  return dt
}

export const datetimeFormat = (timestamp: any) => {
  const dt = getCheckDate(timestamp)
  if (!dt) return timestamp

  const y = dt.getFullYear()
  const m = (dt.getMonth() + 1 + '').padStart(2, '0')
  const d = (dt.getDate() + '').padStart(2, '0')
  const hh = (dt.getHours() + '').padStart(2, '0')
  const mm = (dt.getMinutes() + '').padStart(2, '0')
  const ss = (dt.getSeconds() + '').padStart(2, '0')

  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}

/**
 *
 * string: only accept ISO 8601, example: '2018-04-04T16:00:00.000Z'
 * number: timestamp
 * @param time
 */
export function getDate(time?: Date | string | number) {
  if (!time) return undefined
  if (time instanceof Date) return time
  if (typeof time === 'string') {
    return dayjs(time).toDate()
  }
  return new Date(time)
}

export const getBrowserLocale = () => {
  const language = navigator.language
  if (!language) {
    return 'zh-CN'
  }
  if (language.startsWith('en')) {
    return 'en'
  }
  if (language.toLowerCase().startsWith('zh')) {
    const temp = language.toLowerCase().replace('_', '-')
    return temp === 'zh' ? 'zh-CN' : temp === 'zh-cn' ? 'zh-CN' : 'tw'
  }
  return language
}
export const getLocale = () => {
  return wsCache.get('user.language') || getBrowserLocale() || 'zh-CN'
}

export const setSize = (size: any) => {
  let data = ''
  const _size = Number.parseFloat(size)
  if (_size < 1 * 1024) {
    //如果小于0.1KB转化成B
    data = _size.toFixed(2) + 'B'
  } else if (_size < 1 * 1024 * 1024) {
    //如果小于0.1MB转化成KB
    data = (_size / 1024).toFixed(2) + 'KB'
  } else if (_size < 1 * 1024 * 1024 * 1024) {
    //如果小于0.1GB转化成MB
    data = (_size / (1024 * 1024)).toFixed(2) + 'MB'
  } else {
    //其他转化成GB
    data = (_size / (1024 * 1024 * 1024)).toFixed(2) + 'GB'
  }
  const size_str = data + ''
  const len = size_str.indexOf('.')
  const dec = size_str.substr(len + 1, 2)
  if (dec == '00') {
    //当小数点后为00时 去掉小数部分
    return size_str.substring(0, len) + size_str.substr(len + 3, 2)
  }
  return size_str
}

export const isInIframe = () => {
  try {
    return window.top !== window.self
  } catch (error) {
    console.error(error)
    return true
  }
}

export const isBtnShow = (val: string) => {
  if (!val || val === '0') {
    return true
  } else if (val === '1') {
    return false
  } else {
    return !isInIframe()
  }
}

export const setTitle = (title?: string) => {
  document.title = title || 'SQLBot'
}

function rgbToHex(r: any, g: any, b: any) {
  // 确保数值在0-255范围内
  r = Math.max(0, Math.min(255, r))
  g = Math.max(0, Math.min(255, g))
  b = Math.max(0, Math.min(255, b))

  // 转换为16进制并补零
  const hexR = r.toString(16).padStart(2, '0')
  const hexG = g.toString(16).padStart(2, '0')
  const hexB = b.toString(16).padStart(2, '0')

  return `#${hexR}${hexG}${hexB}`.toUpperCase()
}
function rgbaToHex(r: any, g: any, b: any, a: any) {
  // 处理RGB部分
  const hexR = Math.max(0, Math.min(255, r)).toString(16).padStart(2, '0')
  const hexG = Math.max(0, Math.min(255, g)).toString(16).padStart(2, '0')
  const hexB = Math.max(0, Math.min(255, b)).toString(16).padStart(2, '0')

  // 处理透明度（可选）
  const hexA =
    a !== undefined
      ? Math.round(Math.max(0, Math.min(1, a)) * 255)
          .toString(16)
          .padStart(2, '0')
      : ''

  return `#${hexR}${hexG}${hexB}${hexA}`.toUpperCase()
}

export function colorStringToHex(colorStr: any) {
  if (colorStr.startsWith('#')) return colorStr
  // 提取颜色值
  const rgbRegex =
    /^(rgb|rgba)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(\d+(?:\.\d+)?)\s*)?\)$/
  const match = colorStr.match(rgbRegex)
  if (!match) return null

  const r = parseInt(match[2])
  const g = parseInt(match[3])
  const b = parseInt(match[4])
  const a = match[5] ? parseFloat(match[5]) : undefined

  return a !== undefined ? rgbaToHex(r, g, b, a) : rgbToHex(r, g, b)
}

export const setCurrentColor = (color: any, element: HTMLElement = document.documentElement) => {
  const currentColor = colorStringToHex(color) as any
  if (!currentColor) {
    return
  }
  element.style.setProperty('--ed-color-primary', currentColor)
  element.style.setProperty('--van-blue', currentColor)
  element.style.setProperty(
    '--ed-color-primary-light-5',
    colorFunctions
      .mix(new colorTree('ffffff'), new colorTree(currentColor.substr(1)), { value: 40 })
      .toRGB()
  )
  element.style.setProperty(
    '--ed-color-primary-light-3',
    colorFunctions
      .mix(new colorTree('ffffff'), new colorTree(currentColor.substr(1)), { value: 15 })
      .toRGB()
  )

  element.style.setProperty(
    '--ed-color-primary-60',
    colorFunctions
      .mix(new colorTree('ffffff'), new colorTree(currentColor.substr(1)), { value: 60 })
      .toRGB()
  )

  element.style.setProperty(
    '--ed-color-primary-80',
    colorFunctions
      .mix(new colorTree('ffffff'), new colorTree(currentColor.substr(1)), { value: 80 })
      .toRGB()
  )

  element.style.setProperty(
    '--ed-color-primary-15-d',
    colorFunctions
      .mix(new colorTree('000000'), new colorTree(currentColor.substr(1)), { value: 15 })
      .toRGB()
  )
  element.style.setProperty('--ed-color-primary-1a', `${currentColor}1a`)
  element.style.setProperty('--ed-color-primary-14', `${currentColor}14`)
  element.style.setProperty('--ed-color-primary-33', `${currentColor}33`)
  element.style.setProperty('--ed-color-primary-99', `${currentColor}99`)
  element.style.setProperty(
    '--ed-color-primary-dark-2',
    colorFunctions
      .mix(new colorTree('000000'), new colorTree(currentColor.substr(1)), { value: 15 })
      .toRGB()
  )
}
