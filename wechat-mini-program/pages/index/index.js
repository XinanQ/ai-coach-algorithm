const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    userName: '员工',
    todayReported: false,
    myRank: '--',
    rankScope: '网点排名',
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
    // 字段对齐 GET /api/mini/home：monthlyScore / completionRate / rank / pendingPracticeTaskCount
    api.home.getSummary().then((d) => {
      const myScore = d.monthlyScore || 0
      const scoreTarget = d.scoreTarget || 0
      const scorePercent = d.completionRate != null
        ? d.completionRate
        : (scoreTarget > 0 ? Math.min(100, Math.round((myScore / scoreTarget) * 100)) : 0)
      this.setData({
        userName: d.name || '员工',
        todayReported: d.todayReported,
        myRank: d.rank == null ? '--' : d.rank,
        rankScope: d.rankScope || '网点排名',
        myScore,
        scoreTarget,
        scorePercent,
        scoreRemain: Math.max(0, scoreTarget - myScore),
        practiceTaskCount: d.pendingPracticeTaskCount || 0
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
