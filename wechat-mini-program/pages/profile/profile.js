const auth = require('../../utils/auth')
const apiAuth = require('../../api/auth')

function isOutletProfile(profile) {
  const level = String(profile.level || '').toUpperCase()
  const organizationLevel = String(profile.organizationLevel || '').toUpperCase()
  const organizationName = profile.organizationName || ''
  const position = profile.position || ''

  return level === 'OUTLET' ||
    organizationLevel === 'OUTLET' ||
    organizationName.indexOf('网点') >= 0 ||
    organizationName.indexOf('营业室') >= 0 ||
    position.indexOf('网点') >= 0
}

Page({
  data: {
    userName: '员工',
    branch: '',
    role: '',
    roleLabel: '',
    isAdmin: false,
    canViewReportHistory: false
  },

  onShow() {
    if (!auth.guard()) return
    this.loadProfile()
  },

  loadProfile() {
    apiAuth.getProfile()
        .then((profile) => {
          console.log('我的页 profile 返回：', profile)

          const cachedUser = auth.getUserInfo() || {}
          const mergedProfile = Object.assign({}, cachedUser, profile)
          const isAdmin = Boolean(mergedProfile.isAdmin)
          const role = isAdmin ? 'manager' : 'staff'
          const canViewReportHistory = !isAdmin || isOutletProfile(mergedProfile)

          this.setData({
            userName: mergedProfile.name || '员工',
            branch: mergedProfile.organizationName || '',
            role: role,
            roleLabel: mergedProfile.roleName || (isAdmin ? '管理员' : '普通员工'),
            isAdmin: isAdmin,
            canViewReportHistory: canViewReportHistory
          })

          wx.setStorageSync('userInfo', mergedProfile)
          wx.setStorageSync('role', role)

          if (isAdmin && !canViewReportHistory) {
            this.refreshAccountDetailForOutlet()
          }
        })
        .catch((err) => {
          console.error('加载我的页信息失败：', err)
          wx.showToast({
            title: err.message || '加载个人信息失败',
            icon: 'none'
          })
        })
  },

  refreshAccountDetailForOutlet() {
    apiAuth.getAccount()
      .then((account) => {
        const mergedUser = Object.assign({}, auth.getUserInfo() || {}, account)
        const canViewReportHistory = isOutletProfile(mergedUser)

        wx.setStorageSync('userInfo', mergedUser)
        this.setData({
          branch: mergedUser.organizationName || this.data.branch,
          canViewReportHistory: canViewReportHistory
        })
      })
      .catch(() => {})
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
