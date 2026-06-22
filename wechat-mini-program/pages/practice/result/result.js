const api = require('../../../api/index')

Page({
  data: {
    taskId: '',
    score: 0,
    delta: 6,
    cert: '新晋「合规揭示达人」',
    certDesc: '合规表达达标，完成专项认证',
    dimensions: [],
    rewardPoints: 80,
    rewardExp: 120,
    suggestion: ''
  },
  onLoad(query) {
    const score = Number(query.score || 0)
    const taskId = query.taskId || ''
    this.setData({ taskId })
    api.practice.getResult(taskId, score).then((d) => {
      this.setData({
        score: d.score,
        delta: d.delta,
        cert: d.cert,
        certDesc: d.certDesc,
        dimensions: d.dimensions,
        rewardPoints: d.rewardPoints,
        rewardExp: d.rewardExp,
        suggestion: d.suggestion
      })
    })
  },
  goReview() {
    wx.navigateTo({ url: `/pages/practice/review/review?taskId=${this.data.taskId}` })
  },
  retry() {
    wx.redirectTo({ url: `/pages/practice/chat/chat?taskId=${this.data.taskId}` })
  },
  nextLevel() {
    wx.reLaunch({ url: '/pages/practice/list/list' })
  }
})
