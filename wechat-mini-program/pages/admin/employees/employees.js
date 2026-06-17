const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    employees: []
  },
  onShow() {
    if (!auth.guard('manager')) return
    api.admin.getEmployees().then((employees) => this.setData({ employees }))
  },
  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/admin/employee-detail/employee-detail?id=${id}` })
  }
})
