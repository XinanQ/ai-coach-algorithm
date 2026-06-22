const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    indicators: [
      { id: 1, name: '存款净增额', unit: '万元' },
      { id: 2, name: '理财销售额', unit: '万元' },
      { id: 3, name: '信用卡发卡量', unit: '张' }
    ],
    indicatorIndex: 0,
    value: '',
    fileList: []
  },
  onLoad() {
    api.report.getIndicators().then((indicators) => this.setData({ indicators }))
  },
  onShow() {
    if (!auth.requireLogin()) return
  },
  onIndicatorChange(e) {
    this.setData({ indicatorIndex: Number(e.detail.value) })
  },
  onValueInput(e) {
    this.setData({ value: e.detail.value })
  },
  chooseImage() {
    wx.chooseMedia({
      count: 3 - this.data.fileList.length,
      mediaType: ['image'],
      success: (res) => {
        const files = res.tempFiles.map(f => ({ url: f.tempFilePath }))
        this.setData({ fileList: this.data.fileList.concat(files) })
      }
    })
  },
  removeImage(e) {
    const index = e.currentTarget.dataset.index
    const fileList = this.data.fileList.slice()
    fileList.splice(index, 1)
    this.setData({ fileList })
  },
  submit() {
    if (!this.data.value) {
      wx.showToast({ title: '请输入业绩数值', icon: 'none' })
      return
    }
    const indicator = this.data.indicators[this.data.indicatorIndex] || {}
    // 真实后端需先用 wx.uploadFile 上传图片换取 url，再提交
    const payload = {
      indicatorId: indicator.id,
      value: this.data.value,
      images: this.data.fileList.map((f) => f.url)
    }
    api.report.submit(payload).then(() => {
      wx.showToast({ title: '上报成功', icon: 'success' })
      this.setData({ value: '', fileList: [] })
    })
  }
})
