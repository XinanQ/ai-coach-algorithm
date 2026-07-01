const auth = require('../../../utils/auth')
const api = require('../../../api/index')

// 任务状态枚举 → 中文（后端可能下发枚举，如 IN_PROGRESS）
const STATUS_LABEL = {
  IN_PROGRESS: '进行中',
  PENDING: '待完成',
  NOT_STARTED: '待完成',
  DONE: '已完成',
  FINISHED: '已完成'
}

Page({
  data: {
    growth: {},
    hasGrowth: false,
    growthPercent: 0,
    segs: ['上级下发', '自主练习', '已完成'],
    tabKeys: ['assigned', 'self', 'done'],
    activeTab: 0,
    list: []
  },
  onShow() {
    if (!auth.guard('staff')) return
    this.loadTab()
  },
  loadTab() {
    // 规范：GET /api/mini/practice/tasks?tab=... 每次按 tab 拉取，成长信息随返回体一起来
    const tab = this.data.tabKeys[this.data.activeTab] || 'assigned'
    api.practice.getTasks(tab).then((d) => {
      const points = d.points
      const target = d.target
      const growthPercent = target > 0 ? Math.min(100, Math.round((points / target) * 100)) : 0
      const list = (d.list || []).map((it) => Object.assign({}, it, {
        statusLabel: STATUS_LABEL[it.status] || it.status || ''
      }))
      this.setData({
        hasGrowth: Boolean(d.levelName || points != null || target != null || d.streakDays != null || d.weekGain != null),
        growth: {
          levelName: d.levelName || '',
          points: points != null ? points : '',
          target: target != null ? target : '',
          streakDays: d.streakDays != null ? d.streakDays : '',
          weekGain: d.weekGain != null ? d.weekGain : ''
        },
        growthPercent,
        list
      })
    })
  },
  switchSeg(e) {
    this.setData({ activeTab: Number(e.currentTarget.dataset.index) }, () => this.loadTab())
  },
  goTask(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/practice/intro/intro?taskId=${id}` })
  },
  goHistory() {
    wx.navigateTo({ url: '/pages/practice/history/history' })
  }
})
