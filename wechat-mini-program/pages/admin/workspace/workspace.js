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
    // 规范：GET /api/mini/admin/workspace 单接口返回统计 + 排行
    // period 映射为后端枚举；branchId/position/type 待后端确定取值口径后再接（当前 mock 忽略）
    const filters = {
      period: ['week', 'month', 'quarter'][this.data.periodIndex] || 'week'
    }
    api.admin.getWorkspace(filters).then((d) => {
      this.setData({
        stats: {
          completionRate: d.completionRate,
          completionDelta: d.completionDelta,
          avgScore: d.avgScore,
          avgDelta: d.avgDelta,
          pendingCount: d.pendingCount,
          highRiskCount: d.highRiskCount
        },
        ranking: d.ranking || []
      })
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
