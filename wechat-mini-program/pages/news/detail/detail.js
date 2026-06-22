const api = require('../../../api/index')

Page({
  data: {
    title: '',
    date: '',
    recipient: '',
    imageUrl: '',
    content: ''
  },
  onLoad(query) {
    api.news.getDetail(query.id).then((item) => {
      if (item) this.setData(item)
    })
  },
  saveImage() {
    if (!this.data.imageUrl) {
      wx.showToast({ title: '暂无图片', icon: 'none' })
      return
    }
    wx.saveImageToPhotosAlbum({
      filePath: this.data.imageUrl,
      success: () => wx.showToast({ title: '已保存' })
    })
  }
})
