const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    emp: {}
  },
  onLoad(query) {
    if (!auth.requireLogin()) return
    api.admin.getEmployeeDetail(query.id || '').then((emp) => {
      emp.tasks = emp.tasks.map((t) => ({
        name: t.name,
        status: t.status,
        scoreText: t.score === null ? '—' : t.score + '分'
      }))
      this.setData({ emp })
    })
  },
  reassign() {
    wx.navigateTo({ url: '/pages/admin/assign/assign' })
  }
})
