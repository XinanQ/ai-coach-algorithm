// app.js
const auth = require('./utils/auth')

App({
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 恢复本地登录态（页面守卫据此判断是否需要跳转登录页）
    this.globalData.userInfo = auth.getUserInfo()

    // 微信登录，获取 code 供后端换取身份（接入真实登录后使用）
    // 注意：未接入真实登录前 code 暂时用不到；wx.login 在开发者工具里可能因
    // appid 权限/登录服务抖动而超时，必须加 fail 兜底，否则会冒泡成未捕获的
    // "Error: timeout"。这里失败不阻塞启动。
    wx.login({
      success: res => {
        // TODO: 发送 res.code 到后台换取 openId, sessionKey, unionId
      },
      fail: err => {
        console.warn('[wx.login] 获取 code 失败（不影响 mock 模式下的使用）：', err)
      }
    })
  },
  globalData: {
    userInfo: null
  }
})
