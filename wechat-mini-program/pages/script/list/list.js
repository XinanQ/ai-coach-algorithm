const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    scripts: []
  },
  onShow() {
    if (!auth.guard('staff')) return
    api.script.getList().then((scripts) => this.setData({ scripts }))
  },
  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/script/detail/detail?id=${id}` })
  }
})
