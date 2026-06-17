const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    tabs: ['日', '周', '月'],
    activeTab: 0,
    myRank: 12,
    myScore: 86,
    list: []
  },
  onShow() {
    if (!auth.guard('staff')) return
    this.loadRanking()
  },
  switchTab(e) {
    this.setData({ activeTab: Number(e.currentTarget.dataset.index) })
    this.loadRanking()
  },
  loadRanking() {
    const period = ['day', 'week', 'month'][this.data.activeTab] || 'day'
    api.ranking.getRanking(period).then((d) => {
      this.setData({ myRank: d.myRank, myScore: d.myScore, list: d.list })
    })
  }
})
