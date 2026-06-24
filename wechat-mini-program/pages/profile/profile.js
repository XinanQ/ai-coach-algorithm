const auth = require('../../utils/auth')

Page({
  data: {
    userName: '员工',
    branch: '',
    role: '',
    roleLabel: ''
  },
  onShow() {
    if (!auth.guard()) return
    const user = auth.getUserInfo() || {}
    const role = auth.getRole()
    this.setData({
      userName: user.name || '员工',
      branch: user.organizationName || '',
      role,
      roleLabel: role === 'manager' ? '管理员' : '普通员工'
    })
  },
  // 账户信息（只读详情）
  goAccount() {
    wx.navigateTo({ url: '/pages/account/account' })
  },
  // 员工菜单
  goHistory() {
    wx.navigateTo({ url: '/pages/history/history' })
  },
  goPracticeHistory() {
    wx.navigateTo({ url: '/pages/practice/history/history' })
  },
  goNews() {
    wx.navigateTo({ url: '/pages/news/list/list' })
  },
  // 管理员菜单
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
