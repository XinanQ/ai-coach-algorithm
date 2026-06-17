const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    userName: '员工',
    todayReported: false,
    myRank: '--',
    myScore: 0,
    scoreTarget: 120,
    scorePercent: 0,
    scoreRemain: 0,
    practiceTaskCount: 0
  },
  onShow() {
    if (!auth.guard('staff')) return
    this.loadData()
  },
  loadData() {
    api.home.getSummary().then((d) => {
      const myScore = d.myScore
      const scoreTarget = d.scoreTarget
      const scorePercent = scoreTarget > 0
        ? Math.min(100, Math.round((myScore / scoreTarget) * 100))
        : 0
      this.setData({
        userName: d.userName || '员工',
        todayReported: d.todayReported,
        myRank: d.myRank,
        myScore,
        scoreTarget,
        scorePercent,
        scoreRemain: Math.max(0, scoreTarget - myScore),
        practiceTaskCount: d.practiceTaskCount
      })
    })
  },
  goReport() {
    wx.navigateTo({ url: '/pages/report/report' })
  },
  goRanking() {
    wx.reLaunch({ url: '/pages/ranking/ranking' })
  },
  goPractice() {
    wx.reLaunch({ url: '/pages/practice/list/list' })
  },
  goNews() {
    wx.navigateTo({ url: '/pages/news/list/list' })
  }
})
