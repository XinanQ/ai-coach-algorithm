const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    branches: ['全部支行', '城东支行', '城西支行'],
    branchIndex: 0,
    positions: ['全部岗位', '客户经理', '理财顾问'],
    positionIndex: 0,
    types: ['全部类型', '必须完成', '强烈推荐'],
    typeIndex: 0,
    periods: ['本周', '本月', '本季'],
    periodIndex: 0,
    stats: {},
    ranking: []
  },
  onShow() {
    if (!auth.guard('manager')) return
    this.loadData()
  },
  loadData() {
    const filters = {
      branch: this.data.branches[this.data.branchIndex],
      position: this.data.positions[this.data.positionIndex],
      type: this.data.types[this.data.typeIndex],
      period: this.data.periods[this.data.periodIndex]
    }
    Promise.all([
      api.admin.getWorkspaceStats(filters),
      api.admin.getWorkspaceRanking(filters)
    ]).then(([stats, ranking]) => {
      this.setData({ stats, ranking })
    })
  },
  onBranch(e) { this.setData({ branchIndex: Number(e.detail.value) }, () => this.loadData()) },
  onPosition(e) { this.setData({ positionIndex: Number(e.detail.value) }, () => this.loadData()) },
  onType(e) { this.setData({ typeIndex: Number(e.detail.value) }, () => this.loadData()) },
  onPeriod(e) { this.setData({ periodIndex: Number(e.detail.value) }, () => this.loadData()) },
  goAssign() {
    wx.navigateTo({ url: '/pages/admin/assign/assign' })
  }
})
