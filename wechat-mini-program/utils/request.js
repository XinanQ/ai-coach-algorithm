// wx.request 统一封装
// 约定后端返回信封：{ code: 200, message: '', data: ... }，成功时 resolve data
const config = require('../config')

function buildHeader(extra) {
  const header = { 'content-type': 'application/json' }
  const token = wx.getStorageSync('token')
  // 后端约定：自定义头 X-Auth-Token，不是 Authorization，也不带 Bearer 前缀
  if (token) header['X-Auth-Token'] = token
  return Object.assign(header, extra || {})
}

function request(method, url, data, options) {
  options = options || {}
  return new Promise((resolve, reject) => {
    wx.request({
      url: config.BASE_URL + config.API_PREFIX + url,
      method,
      data,
      header: buildHeader(options.header),
      success(res) {
        const statusCode = res.statusCode
        const body = res.data

        // 登录态失效：清登录态并回登录页
        if (statusCode === 401) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          wx.removeStorageSync('role')
          wx.reLaunch({ url: '/pages/login/login' })
          reject(new Error('登录已过期，请重新登录'))
          return
        }

        // 后端约定：业务成功码为 200（不是 0）
        if (statusCode >= 200 && statusCode < 300 && body && body.code === 200) {
          resolve(body.data)
          return
        }

        const msg = (body && body.message) || ('请求失败(' + statusCode + ')')
        if (!options.silent) wx.showToast({ title: msg, icon: 'none' })
        reject(new Error(msg))
      },
      fail(err) {
        if (!options.silent) wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' })
        reject(err)
      }
    })
  })
}

// 文件上传（图片等），配合 wx.uploadFile
function upload(url, filePath, name, formData) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: config.BASE_URL + config.API_PREFIX + url,
      filePath,
      name: name || 'file',
      formData: formData || {},
      header: buildHeader(),
      success(res) {
        try {
          const body = JSON.parse(res.data)
          if (body && body.code === 200) {
            resolve(body.data)
          } else {
            reject(new Error((body && body.message) || '上传失败'))
          }
        } catch (e) {
          reject(new Error('上传响应解析失败'))
        }
      },
      fail: reject
    })
  })
}

module.exports = {
  request,
  upload,
  get: (url, data, options) => request('GET', url, data, options),
  post: (url, data, options) => request('POST', url, data, options),
  put: (url, data, options) => request('PUT', url, data, options),
  del: (url, data, options) => request('DELETE', url, data, options)
}
