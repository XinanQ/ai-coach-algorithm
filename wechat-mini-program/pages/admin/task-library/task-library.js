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
  goAssign(e) {
    // 从模板行进入时带上 templateId，下发页据此预填名称/维度
    const id = e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id
    const url = id ? `/pages/admin/assign/assign?templateId=${id}` : '/pages/admin/assign/assign'
    wx.navigateTo({ url })
  }
})
