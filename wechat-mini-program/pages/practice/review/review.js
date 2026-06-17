const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    taskId: '',
    original: '',
    optimized: '',
    saved: false
  },
  onLoad(query) {
    if (!auth.requireLogin()) return
    this.setData({ taskId: query.taskId || '' })
    this.loadReview()
  },
  loadReview() {
    api.practice.getReview(this.data.taskId).then((d) => {
      this.setData({ original: d.original, optimized: d.optimized })
    })
  },
  save() {
    if (this.data.saved) return
    api.script.save({ taskId: this.data.taskId, optimized: this.data.optimized }).then(() => {
      this.setData({ saved: true })
      wx.showToast({ title: '已收藏到话术库', icon: 'success' })
    })
  },
  goLibrary() {
    wx.reLaunch({ url: '/pages/script/list/list' })
  },
  done() {
    wx.reLaunch({ url: '/pages/practice/list/list' })
  }
})
