import { defineStore } from 'pinia'
import { store } from '@/stores/index'
// import { defaultFont, list } from '@/api/font'
import { request } from '@/utils/request'

import { setTitle, setCurrentColor } from '@/utils/utils'

const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/appearance/picture/'
import { isBtnShow } from '@/utils/utils'
interface AppearanceState {
  themeColor?: string
  customColor?: string
  navigateBg?: string
  navigate?: string
  mobileLogin?: string
  mobileLoginBg?: string
  help?: string
  showAi?: string
  showCopilot?: string
  showDoc?: string
  showAbout?: string
  bg?: string
  login?: string
  slogan?: string
  web?: string
  name?: string
  foot?: string
  showSlogan?: string
  pc_welcome?: string
  pc_welcome_desc?: string
  footContent?: string
  loaded: boolean
  showDemoTips?: boolean
  demoTipsContent?: string
  fontList?: Array<{ name: string; id: string; isDefault: boolean }>
}

interface KeyValue {
  pkey: string
  pval: string
}
// const { wsCache } = useCache()
export const useAppearanceStore = defineStore('appearanceStore', {
  state: (): AppearanceState => {
    return {
      themeColor: '',
      customColor: '',
      navigateBg: '',
      navigate: '',
      mobileLogin: '',
      mobileLoginBg: '',
      help: '',
      showDoc: '0',
      showSlogan: '0',
      showAi: '0',
      showCopilot: '0',
      showAbout: '0',
      bg: '',
      login: '',
      slogan: '',
      web: '',
      name: 'SQLBot',
      foot: 'false',
      footContent: '',
      loaded: false,
      showDemoTips: false,
      demoTipsContent: '',
      fontList: [],
      pc_welcome: undefined,
      pc_welcome_desc: undefined,
    }
  },
  getters: {
    getNavigate(): string {
      if (this.navigate) {
        return baseUrl + this.navigate
      }
      return null!
    },
    getMobileLogin(): string {
      if (this.mobileLogin) {
        return baseUrl + this.mobileLogin
      }
      return null!
    },
    getMobileLoginBg(): string {
      if (this.mobileLoginBg) {
        return baseUrl + this.mobileLoginBg
      }
      return null!
    },
    getHelp(): string {
      return this.help!
    },
    getThemeColor(): string {
      return this.themeColor!
    },
    isBlue(): boolean {
      return this.themeColor! === 'blue'
    },
    getCustomColor(): string {
      return this.customColor!
    },
    getNavigateBg(): string {
      return this.navigateBg!
    },
    getBg(): string {
      if (this.bg) {
        return baseUrl + this.bg
      }
      return null!
    },
    getLogin(): string {
      if (this.login) {
        return baseUrl + this.login
      }
      return null!
    },
    getSlogan(): string {
      return this.slogan!
    },
    getWeb(): string {
      if (this.web) {
        return baseUrl + this.web
      }
      return null!
    },
    getName(): string {
      return this.name!
    },
    getLoaded(): boolean {
      return this.loaded
    },
    getFoot(): string {
      return this.foot!
    },
    getFootContent(): string {
      return this.footContent!
    },
    getShowDemoTips(): boolean {
      return this.showDemoTips!
    },
    getDemoTipsContent(): string {
      return this.demoTipsContent!
    },
    getShowAi(): boolean {
      return isBtnShow(this.showAi!)
    },
    getShowCopilot(): boolean {
      return isBtnShow(this.showCopilot!)
    },
    getShowSlogan(): boolean {
      return isBtnShow(this.showSlogan!)
    },
    getShowDoc(): boolean {
      return isBtnShow(this.showDoc!)
    },
    getShowAbout(): boolean {
      return isBtnShow(this.showAbout!)
    },
  },
  actions: {
    setNavigate(data: string) {
      this.navigate = data
    },
    setMobileLogin(data: string) {
      this.mobileLogin = data
    },
    // async setFontList() {
    //   const res = await list()
    //   this.fontList = res || []
    // },
    // setCurrentFont(name) {
    //   const currentFont = this.fontList.find(ele => ele.name === name)
    //   if (currentFont) {
    //     let fontStyleElement = document.querySelector(`#de-custom_font${name}`)
    //     if (!fontStyleElement) {
    //       fontStyleElement = document.createElement('style')
    //       fontStyleElement.setAttribute('id', `de-custom_font${name}`)
    //       document.querySelector('head').appendChild(fontStyleElement)
    //     }
    //     fontStyleElement.innerHTML = `@font-face {
    //         font-family: '${name}';
    //         src: url(${
    //           embeddedStore.baseUrl
    //             ? (embeddedStore.baseUrl + basePath).replace('/./', '/')
    //             : basePath
    //         }/typeface/download/${currentFont.fileTransName});
    //         font-weight: normal;
    //         font-style: normal;
    //         }`
    //   }
    // },
    setMobileLoginBg(data: string) {
      this.mobileLoginBg = data
    },
    setHelp(data: string) {
      this.help = data
    },
    setNavigateBg(data: string) {
      this.navigateBg = data
    },
    setThemeColor(data: string) {
      this.themeColor = data
    },
    setCustomColor(data: string) {
      this.customColor = data
    },
    setLoaded(data: boolean) {
      this.loaded = data
    },
    async setAppearance() {
      // const desktop = wsCache.get('app.desktop')
      // if (desktop) {
      //   this.loaded = true
      //   this.community = true
      // }
      if (this.loaded) {
        return
      }
      // defaultFont().then(res => {
      //   const [font] = res || []
      //   setDefaultFont(
      //     `${
      //       embeddedStore.baseUrl
      //         ? (embeddedStore.baseUrl + basePath).replace('/./', '/')
      //         : basePath
      //     }/typeface/download/${font?.fileTransName}`,
      //     font?.name,
      //     font?.fileTransName
      //   )
      //   function setDefaultFont(url, name, fileTransName) {
      //     let fontStyleElement = document.querySelector('#de-custom_font')
      //     if (!fontStyleElement) {
      //       fontStyleElement = document.createElement('style')
      //       fontStyleElement.setAttribute('id', 'de-custom_font')
      //       document.querySelector('head').appendChild(fontStyleElement)
      //     }
      //     fontStyleElement.innerHTML =
      //       name && fileTransName
      //         ? `@font-face {
      //           font-family: '${name}';
      //           src: url(${url});
      //           font-weight: normal;
      //           font-style: normal;
      //           }`
      //         : ''
      //     document.documentElement.style.setProperty('--de-custom_font', `${name}`)
      //     document.documentElement.style.setProperty('--van-base-font', `${name}`)
      //   }
      // })
      // if (!isDataEaseBi) {
      //   document.title = ''
      // }
      const obj = LicenseGenerator.getLicense()
      if (obj?.status !== 'valid') {
        setCurrentColor('#1CBA90')
        document.title = 'SQLBot'
        setLinkIcon()
        return
      }
      const resData = await request.get('/system/appearance/ui')
      this.loaded = true
      if (!resData?.length) {
        setCurrentColor('#1CBA90')
        setLinkIcon()
        return
      }
      const data: AppearanceState = { loaded: false }
      resData.forEach((item: KeyValue) => {
        ;(
          data as {
            [key: string]: any
          }
        )[item.pkey] = item.pval
      })
      this.navigate = data.navigate
      this.help = data.help
      this.showDoc = data.showDoc
      this.showAbout = data.showAbout
      this.navigateBg = data.navigateBg
      this.themeColor = data.themeColor
      this.customColor = data.customColor
      this.pc_welcome = data.pc_welcome
      this.pc_welcome_desc = data.pc_welcome_desc
      const currentColor =
        this.themeColor === 'custom' && this.customColor
          ? this.customColor
          : this.isBlue
            ? '#3370ff'
            : '#1CBA90'
      setCurrentColor(currentColor)
      this.bg = data.bg
      this.login = data.login
      this.slogan = data.slogan
      this.showSlogan = data.showSlogan
      this.web = data.web
      this.name = data.name
      if (this.name) {
        document.title = this.name
        setTitle(this.name)
      } else {
        document.title = 'SQLBot'
        setTitle('SQLBot')
      }
      setLinkIcon(this.web)
    },
  },
})

const setLinkIcon = (linkWeb?: string) => {
  const link = document.querySelector('link[rel="icon"]') as HTMLLinkElement
  if (link) {
    if (linkWeb) {
      link['href'] = baseUrl + linkWeb
    } else {
      link['href'] = '/LOGO-fold.svg'
    }
  }
}

export const useAppearanceStoreWithOut = () => {
  return useAppearanceStore(store)
}
