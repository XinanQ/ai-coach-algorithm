const auth = require('../../utils/auth')
const apiAuth = require('../../api/auth')

Page({
  data: {
    userName: '员工',
    branch: '',
    role: '',
    roleLabel: '',
    isAdmin: false
  },

  onShow() {
    if (!auth.guard()) return
    this.loadProfile()
  },

  loadProfile() {
    apiAuth.getProfile()
        .then((profile) => {
          console.log('我的页 profile 返回：', profile)

          const isAdmin = Boolean(profile.isAdmin)
          const role = isAdmin ? 'manager' : 'staff'

          this.setData({
            userName: profile.name || '员工',
            branch: profile.organizationName || '',
            role: role,
            roleLabel: profile.roleName || (isAdmin ? '管理员' : '普通员工'),
            isAdmin: isAdmin
          })

          wx.setStorageSync('userInfo', profile)
          wx.setStorageSync('role', role)
        })
        .catch((err) => {
          console.error('加载我的页信息失败：', err)
          wx.showToast({
            title: err.message || '加载个人信息失败',
            icon: 'none'
          })
        })
  },

  goAccount() {
    wx.navigateTo({ url: '/pages/account/account' })
  },

  goHistory() {
    wx.navigateTo({ url: '/pages/history/history' })
  },

  goPracticeHistory() {
    wx.navigateTo({ url: '/pages/practice/history/history' })
  },

  goNews() {
    wx.navigateTo({ url: '/pages/news/list/list' })
  },

  goAnalysis() {
    wx.reLaunch({ url: '/pages/admin/analysis/analysis' })
  },

  goEmployees() {
    wx.reLaunch({ url: '/pages/admin/employees/employees' })
  },

  goTaskLib() {
    wx.reLaunch({ url: '/pages/admin/task-library/task-library' })
  },

  switchRole() {
    if (!this.data.isAdmin) {
      wx.showToast({
        title: '无管理员权限',
        icon: 'none'
      })
      return
    }

    wx.reLaunch({ url: '/pages/role/role' })
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      confirmColor: '#111111',
      success: (res) => {
        if (res.confirm) {
          auth.logout()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  }
})
