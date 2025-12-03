// src/services/request.ts
import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
  type CancelTokenSource,
} from 'axios'

import { useCache } from '@/utils/useCache'
import { getLocale } from './utils'
import { useAssistantStore } from '@/stores/assistant'
import { useRouter } from 'vue-router'
import JSONBig from 'json-bigint'
// import { i18n } from '@/i18n'
// const t = i18n.global.t
const assistantStore = useAssistantStore()
const { wsCache } = useCache()
const router = useRouter()
// Response data structure
export interface ApiResponse<T = unknown> {
  code: number
  data: T
  message: string
  success: boolean
  [key: string]: any // Allow additional fields
}

// Extended request options
export interface RequestOptions {
  silent?: boolean // Silent mode (no error alerts)
  rawResponse?: boolean // Return raw Axios response
  customError?: boolean // Custom error handling
  retryCount?: number // Number of retry attempts
}

// Merged request configuration
export interface FullRequestConfig extends AxiosRequestConfig {
  requestOptions?: RequestOptions
}

// Custom error type
export interface RequestError<T = any> extends Error {
  config: FullRequestConfig
  code?: string
  request?: any
  response?: AxiosResponse<T>
  isAxiosError: boolean
}

class HttpService {
  private instance: AxiosInstance
  private cancelTokenSource: CancelTokenSource

  constructor(config?: AxiosRequestConfig) {
    this.cancelTokenSource = axios.CancelToken.source()
    this.instance = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
      timeout: 100000,
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      // add transformResponse to bigint
      transformResponse: [
        function (data) {
          try {
            return JSONBig.parse(data) // use JSON-bigint
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
          } catch (e) {
            try {
              return JSON.parse(data)
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch (parseError) {
              return data
            }
          }
        },
      ],
      ...config,
    })

    this.setupInterceptors()
  }

  /* private cancelCurrentRequest(message: string) {
    this.cancelTokenSource.cancel(message)
    this.cancelTokenSource = axios.CancelToken.source()
  } */

  private setupInterceptors() {
    // Request interceptor
    this.instance.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        // Add auth token
        const token = wsCache.get('user.token')
        if (token && config.headers) {
          config.headers['X-SQLBOT-TOKEN'] = `Bearer ${token}`
        }
        if (assistantStore.getToken) {
          const prefix = assistantStore.getType === 4 ? 'Embedded ' : 'Assistant '
          config.headers['X-SQLBOT-ASSISTANT-TOKEN'] = `${prefix}${assistantStore.getToken}`
          if (config.headers['X-SQLBOT-TOKEN']) config.headers.delete('X-SQLBOT-TOKEN')
          if (
            assistantStore.getType &&
            !!(assistantStore.getType % 2) &&
            assistantStore.getCertificate
          ) {
            if (config.method?.toLowerCase() === 'get' && /\/chat\/\d+$/.test(config.url || '')) {
              await assistantStore.refreshCertificate()
            }
            config.headers['X-SQLBOT-ASSISTANT-CERTIFICATE'] = btoa(
              encodeURIComponent(assistantStore.getCertificate)
            )
          }
          if (!assistantStore.getType || assistantStore.getType === 2) {
            config.headers['X-SQLBOT-ASSISTANT-ONLINE'] = assistantStore.getOnline
          }
          if (assistantStore.getHostOrigin) {
            config.headers['X-SQLBOT-HOST-ORIGIN'] = assistantStore.getHostOrigin
          }
        }
        const locale = getLocale()
        if (locale) {
          /* const mapping = {
            'zh-CN': 'zh-CN',
            en: 'en-US',
            tw: 'zh-TW',
          } */
          /* const val = mapping[locale] || locale */
          config.headers['Accept-Language'] = locale
        }
        if (config.url?.includes('/xpack_static/') && config.baseURL) {
          config.baseURL = config.baseURL.replace('/api/v1', '')
          // Skip auth for xpack_static requests
          return config
        }

        /* try {
          const request_key = LicenseGenerator.generate()
          config.headers['X-SQLBOT-KEY'] = request_key
        } catch (e: any) {
          if (e?.message?.includes('offline')) {
            this.cancelCurrentRequest('license-key error detected')
            showLicenseKeyError()
          }
        } */

        // Request logging
        // console.log(`[Request] ${config.method?.toUpperCase()} ${config.url}`)

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )
    // Response interceptor
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        // console.log(`[Response] ${response.config.url}`, response.data)

        // Return raw response if configured
        if ((response.config as FullRequestConfig).requestOptions?.rawResponse) {
          return response
        }

        // Handle business logic
        /* if (response.data?.success !== true) {
          return Promise.reject(response.data)
        } */
        if (response.data?.code === 0) {
          return response.data.data
        } else if (response.data?.code) {
          return Promise.reject(response.data)
        }
        return response.data
      },
      async (error: AxiosError) => {
        const config = error.config as FullRequestConfig & { __retryCount?: number }
        const requestOptions = config?.requestOptions || {}

        // Retry logic for specific status codes
        const shouldRetry =
          error.response?.status === 502 &&
          (config.__retryCount || 0) < (requestOptions.retryCount || 3)

        if (shouldRetry) {
          config.__retryCount = (config.__retryCount || 0) + 1

          // Exponential backoff
          await new Promise((resolve) => setTimeout(resolve, 1000 * (config.__retryCount || 1)))

          return this.instance.request(config)
        }

        // Unified error handling
        if (!requestOptions.customError && !requestOptions.silent) {
          this.handleError(error)
        }

        return Promise.reject(error)
      }
    )
  }

  private handleError(error: AxiosError) {
    let errorMessage = 'Request error'

    if (error.response) {
      switch (error.response.status) {
        case 400:
          errorMessage = 'Invalid request parameters'
          break
        case 401:
          errorMessage = error.response?.data
            ? error.response.data.toString()
            : 'Unauthorized, please login again'
          // Redirect to login page if needed
          if (assistantStore.getAssistant) {
            wsCache.delete('user.token')
            if (router?.push) {
              router.push(`/401?title=${encodeURIComponent(errorMessage)}`)
            } else {
              window.location.href = `/#/401?title=${encodeURIComponent(errorMessage)}`
            }
            return
          }
          ElMessage({
            message: errorMessage,
            type: 'error',
            showClose: true,
          })
          setTimeout(() => {
            wsCache.delete('user.token')
            window.location.reload()
          }, 2000)
          return
        // break
        case 403:
          errorMessage = 'Access denied'
          break
        case 404:
          errorMessage = 'Resource not found'
          break
        case 500:
          errorMessage = 'Server error'
          break
        default:
          errorMessage = `Server responded with error: ${error.response.status}`
      }
      if (error?.response?.data) {
        errorMessage = error.response.data.toString()
      }
    } else if (error.request) {
      errorMessage = 'No response from server'
    } else if (axios.isCancel(error)) {
      errorMessage = 'Request canceled'
      return // Skip showing cancel messages
    } else {
      errorMessage = error['message'] || 'Unknown error'
    }

    // Show error using UI library (e.g., Element Plus, Ant Design)
    console.error(errorMessage)
    /* if (errorMessage?.includes('Invalid license key salt')) {
      showLicenseKeyError()
    } */
    // ElMessage.error(errorMessage)
    ElMessage({
      message: errorMessage,
      type: 'error',
      showClose: true,
    })
  }

  // Cancel all pending requests
  public cancelRequests(message?: string) {
    this.cancelTokenSource.cancel(message)
    // Create new token source for future requests
    this.cancelTokenSource = axios.CancelToken.source()
  }

  // Base request method
  public request<T = any>(config: FullRequestConfig): Promise<T> {
    return this.instance.request({
      cancelToken: this.cancelTokenSource.token,
      ...config,
    })
  }

  // GET request
  public get<T = any>(url: string, config?: FullRequestConfig): Promise<T> {
    return this.request({ ...config, method: 'GET', url })
  }

  // POST request
  public post<T = any>(url: string, data?: any, config?: FullRequestConfig): Promise<T> {
    return this.request({ ...config, method: 'POST', url, data })
  }

  public async fetchStream(url: string, data?: any, controller?: AbortController): Promise<any> {
    const token = wsCache.get('user.token')
    const heads: any = {
      'Content-Type': 'application/json',
    }
    if (token) {
      heads['X-SQLBOT-TOKEN'] = `Bearer ${token}`
    }
    if (assistantStore.getToken) {
      const prefix = assistantStore.getType === 4 ? 'Embedded ' : 'Assistant '
      heads['X-SQLBOT-ASSISTANT-TOKEN'] = `${prefix}${assistantStore.getToken}`
      if (heads['X-SQLBOT-TOKEN']) delete heads['X-SQLBOT-TOKEN']
      if (
        assistantStore.getType &&
        !!(assistantStore.getType % 2) &&
        assistantStore.getCertificate
      ) {
        await assistantStore.refreshCertificate()
        heads['X-SQLBOT-ASSISTANT-CERTIFICATE'] = btoa(
          encodeURIComponent(assistantStore.getCertificate)
        )
      }
      if (assistantStore.getHostOrigin) {
        heads['X-SQLBOT-HOST-ORIGIN'] = assistantStore.getHostOrigin
      }
      if (!assistantStore.getType || assistantStore.getType === 2) {
        heads['X-SQLBOT-ASSISTANT-ONLINE'] = assistantStore.getOnline
      }
    }

    /* try {
      const request_key = LicenseGenerator.generate()
      heads['X-SQLBOT-KEY'] = request_key
    } catch (e: any) {
      if (e?.message?.includes('offline')) {
        controller?.abort('license-key error detected')
        showLicenseKeyError()
      }
    } */

    const real_url = import.meta.env.VITE_API_BASE_URL
    return fetch(real_url + url, {
      method: 'POST',
      headers: heads,
      body: JSON.stringify(data),
      signal: controller?.signal,
    })
  }

  // PUT request
  public put<T = any>(url: string, data?: any, config?: FullRequestConfig): Promise<T> {
    return this.request({ ...config, method: 'PUT', url, data })
  }

  // DELETE request
  public delete<T = any>(url: string, config?: FullRequestConfig): Promise<T> {
    return this.request({ ...config, method: 'DELETE', url })
  }

  // PATCH request
  public patch<T = any>(url: string, data?: any, config?: FullRequestConfig): Promise<T> {
    return this.request({ ...config, method: 'PATCH', url, data })
  }

  // File upload
  public upload<T = any>(
    url: string,
    file: File,
    fieldName = 'file',
    config?: FullRequestConfig
  ): Promise<T> {
    const formData = new FormData()
    formData.append(fieldName, file)

    return this.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      ...config,
    })
  }

  // Download file
  public download(url: string, config?: FullRequestConfig): Promise<Blob> {
    return this.request<Blob>({
      ...config,
      method: 'GET',
      url,
      responseType: 'blob',
    })
  }

  public loadRemoteScript(url: string, id?: string, cb?: any): Promise<HTMLElement> {
    if (!url) {
      return Promise.reject(new Error('URL is required to load remote script'))
    }
    if (id && document.getElementById(id)) {
      return Promise.resolve(document.getElementById(id) as HTMLElement)
    }
    if (url.startsWith('/')) {
      const real_url = import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '')
      url = real_url + url
    }
    return new Promise<HTMLElement>((resolve, reject) => {
      // 改用传统的script标签加载方式
      const script = document.createElement('script')
      script.src = url
      script.id = id || `remote-script-${Date.now()}`

      script.onload = () => {
        if (cb) cb()
        resolve(script)
      }

      script.onerror = (error) => {
        console.error(`Failed to load script from ${url}:`, error)
        reject(new Error(`Failed to load script from ${url}`))
      }

      document.head.appendChild(script)
    })
  }
  /* public loadRemoteScript(url: string, id?: string, cb?: any): Promise<HTMLElement> {
    if (!url) {
      return Promise.reject(new Error('URL is required to load remote script'))
    }
    if (id && document.getElementById(id)) {
      return Promise.resolve(document.getElementById(id) as HTMLElement)
    }
    return new Promise<HTMLElement>((resolve, reject) => {
      this.get(url, {
        responseType: 'text',
        headers: {
          'Content-Type': 'application/javascript',
        },
      })
        .then((response: any) => {
          const script = document.createElement('script')
          script.textContent = response
          script.id = id || `remote-script-${Date.now()}`
          // Append script to head
          document.head.appendChild(script)
          if (cb) {
            cb()
          }
          resolve(script)
        })
        .catch((error: any) => {
          console.error(`Failed to load script from ${url}:`, error)
          reject(new Error(`Failed to load script from ${url}: ${error.message}`))
        })
    })
  } */
}

// Create singleton instance
export const request = new HttpService({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})
/*
const showLicenseKeyError = (msg?: string) => {
  ElMessageBox.confirm(t('license.error_tips'), {
    confirmButtonType: 'primary',
    tip: msg || t('license.offline_tips'),
    confirmButtonText: t('common.refresh'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (value: string) => {
      if (value === 'confirm') {
        window.location.reload()
      }
    },
  })
}
 */
