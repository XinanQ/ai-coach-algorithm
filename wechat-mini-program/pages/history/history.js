const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    records: [],
    loading: false
  },

  onShow() {
    if (!auth.requireLogin()) return
    this.loadHistory()
  },

  loadHistory() {
    this.setData({ loading: true })
    api.report.getHistory()
      .then((records) => {
        this.setData({
          records: records || [],
          loading: false
        })
      })
      .catch((err) => {
        this.setData({ loading: false })
        wx.showToast({ title: err.message || '加载上报历史失败', icon: 'none' })
      })
  }
})
