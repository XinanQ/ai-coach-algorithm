const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    growth: {},
    growthPercent: 0,
    segs: ['上级下发', '自主练习', '已完成'],
    activeTab: 0,
    assignedTasks: [],
    libraryTasks: [],
    doneTasks: []
  },
  onShow() {
    if (!auth.guard('staff')) return
    this.loadData()
  },
  loadData() {
    Promise.all([api.practice.getGrowth(), api.practice.getTasks()]).then(([growth, t]) => {
      const growthPercent = growth.target > 0
        ? Math.min(100, Math.round((growth.points / growth.target) * 100))
        : 0
      this.setData({
        growth,
        growthPercent,
        assignedTasks: t.assigned,
        libraryTasks: t.library,
        doneTasks: t.done
      })
    })
  },
  switchSeg(e) {
    this.setData({ activeTab: Number(e.currentTarget.dataset.index) })
  },
  goTask(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/practice/intro/intro?taskId=${id}` })
  },
  goHistory() {
    wx.navigateTo({ url: '/pages/practice/history/history' })
  }
})
