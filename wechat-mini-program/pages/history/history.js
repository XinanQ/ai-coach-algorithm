const api = require('../../api/index')

Page({
  data: {
    records: []
  },
  onLoad() {
    api.report.getHistory().then((records) => this.setData({ records }))
  }
})
