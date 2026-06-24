const config = require('../../config')
const auth = require('../../utils/auth')

Page({
  data: {
    empId: '',
    password: '',
    loading: false
  },

  onLoad() {
    // 已登录则按角色直达对应首页，避免重复登录
    if (auth.isLoggedIn()) {
      const role = auth.getRole()
      wx.reLaunch({ url: role ? auth.homeUrl(role) : '/pages/role/role' })
    }
  },

  onEmpIdInput(e) {
    this.setData({ empId: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onLogin() {
    const empId = this.data.empId.trim()
    const password = this.data.password

    if (!empId) {
      wx.showToast({ title: '请输入工号', icon: 'none' })
      return
    }
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    auth.login(empId, password)
      .then((userInfo) => {
        wx.showToast({ title: '登录成功', icon: 'success' })
      
        setTimeout(() => {
          if (config.USE_MOCK) {
            wx.reLaunch({ url: '/pages/role/role' })
            return
          }
      
          wx.reLaunch({
            url: auth.homeUrl(userInfo.role)
          })
        }, 600)
      })
      .catch((err) => {
        this.setData({ loading: false })
        wx.showToast({ title: err.message || '登录失败', icon: 'none' })
      })
  }
})
