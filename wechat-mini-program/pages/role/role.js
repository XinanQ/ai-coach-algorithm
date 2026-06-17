const auth = require('../../utils/auth')

Page({
  onLoad() {
    // 未登录则回登录页
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
    }
  },
  choose(e) {
    const role = e.currentTarget.dataset.role
    auth.setRole(role)
    wx.reLaunch({ url: auth.homeUrl(role) })
  }
})
