const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    templates: []
  },
  onShow() {
    if (!auth.guard('manager')) return
    api.admin.getTaskTemplates().then((templates) => this.setData({ templates }))
  },
  goAssign() {
    wx.navigateTo({ url: '/pages/admin/assign/assign' })
  }
})
