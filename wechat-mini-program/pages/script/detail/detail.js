const api = require('../../../api/index')

Page({
  data: {
    detail: {},
    displayContent: ''
  },
  onLoad(query) {
    api.script.getDetail(query.id || '').then((detail) => {
      this.setData({
        detail,
        displayContent: detail.standard || detail.content || ''
      })
    })
  },
  copy() {
    const content = this.data.displayContent
    if (!content) return
    wx.setClipboardData({ data: content })
  }
})
