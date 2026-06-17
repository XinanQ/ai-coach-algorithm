const api = require('../../../api/index')

Page({
  data: {
    detail: {},
    standardOnly: false
  },
  onLoad(query) {
    // standard=1 时来自任务详情「查看标准话术」，只看标准话术
    api.script.getDetail(query.id || '').then((detail) => {
      this.setData({ detail, standardOnly: query.standard === '1' })
    })
  },
  copy() {
    wx.setClipboardData({ data: this.data.detail.standard })
  }
})
