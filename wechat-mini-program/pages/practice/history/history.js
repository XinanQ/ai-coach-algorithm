const api = require('../../../api/index')

Page({
  data: {
    records: []
  },
  onLoad() {
    api.practice.getHistory().then((records) => this.setData({ records }))
  },
  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/practice/result/result?taskId=${id}` })
  }
})
