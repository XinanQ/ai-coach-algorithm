Page({
  data: {
    hasResult: false,
    taskId: '',
    resultId: '',
    score: null,
    dimensionScores: [],
    weakTags: [],
    suggestion: '',
    source: ''
  },
  onLoad(query) {
    const sessionId = decodeURIComponent(query.sessionId || '')
    const taskId = decodeURIComponent(query.taskId || '')
    const cacheKey = `practiceFinishResult:${sessionId}`
    const result = sessionId ? wx.getStorageSync(cacheKey) : null

    if (!result || typeof result !== 'object') {
      this.setData({ taskId })
      wx.showToast({
        title: '未找到本次陪练结果，请重新完成陪练',
        icon: 'none'
      })
      return
    }

    wx.removeStorageSync(cacheKey)
    this.setData({
      hasResult: true,
      taskId: result.taskId || taskId,
      resultId: result.resultId || '',
      score: result.score != null ? result.score : null,
      dimensionScores: Array.isArray(result.dimensionScores) ? result.dimensionScores : [],
      weakTags: Array.isArray(result.weakTags) ? result.weakTags : [],
      suggestion: result.suggestion || '',
      source: result.source || ''
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
