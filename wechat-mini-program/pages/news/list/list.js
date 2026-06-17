const api = require('../../../api/index')

Page({
  data: {
    list: []
  },
  onLoad() {
    api.news.getList().then((list) => this.setData({ list }))
  },
  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/news/detail/detail?id=${id}` })
  }
})
