const api = require('../../../api/index')

Page({
  data: {
    taskId: '',
    scene: '',
    customerName: '',
    customerDesc: '',
    tags: [],
    rounds: 3,
    background: '',
    goal: '',
    requirements: [],
    duration: '',
    progress: 0
  },
  onLoad(query) {
    this.setData({ taskId: query.taskId || '' })
    this.loadScene()
  },
  loadScene() {
    api.practice.getTaskDetail(this.data.taskId).then((d) => this.setData(d))
  },
  viewStandard() {
    wx.navigateTo({ url: `/pages/script/detail/detail?taskId=${this.data.taskId}&standard=1` })
  },
  startPractice() {
    wx.navigateTo({ url: `/pages/practice/chat/chat?taskId=${this.data.taskId}` })
  }
})
