const auth = require('../../utils/auth')
Page({
  data: {
    isAdmin: false
  },

  onLoad() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }

    const user = auth.getUserInfo() || {}

    this.setData({
      isAdmin: Boolean(user.isAdmin)
    })
  },

  choose(e) {
    const role = e.currentTarget.dataset.role
    const user = auth.getUserInfo() || {}

    if (role === 'manager' && !user.isAdmin) {
      wx.showToast({
        title: '无管理员权限',
        icon: 'none'
      })
      return
    }

    const ok = auth.setRole(role)
    if (ok === false) {
      wx.showToast({
        title: '无管理员权限',
        icon: 'none'
      })
      return
    }

    wx.reLaunch({ url: auth.homeUrl(role) })
  }
})