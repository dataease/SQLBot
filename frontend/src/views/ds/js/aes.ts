import CryptoJS from 'crypto-js'

// Legacy request format. Storage encryption happens on the server.
const key = CryptoJS.enc.Utf8.parse('SQLBot1234567890')

export const encrypted = (str: string) => {
  return CryptoJS.AES.encrypt(str, key, {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
  }).toString()
}
