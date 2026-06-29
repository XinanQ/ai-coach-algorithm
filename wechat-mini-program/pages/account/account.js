const auth = require('../../utils/auth')
const apiAuth = require('../../api/auth')

Page({
  data: {
    name: '',
    org: '',
    fields: []
  },

  onLoad() {
    if (!auth.requireLogin()) return
    this.loadAccount()
  },

  loadAccount() {
    apiAuth.getAccount()
        .then((account) => {
          console.log('账号详情 account 返回：', account)
          this.render(account)
        })
        .catch((err) => {
          console.error('加载账号详情失败：', err)
          wx.showToast({
            title: err.message || '加载账号信息失败',
            icon: 'none'
          })

          // 兜底：如果接口失败，至少显示本地缓存里的摘要信息
          this.render(auth.getUserInfo() || {})
        })
  },

  render(d) {
    if (!d) return

    const dash = (v) => {
      return v === undefined || v === null || v === '' ? '—' : v
    }

    this.setData({
      name: d.name || '—',
      org: d.organizationName || '',
      fields: [
        { label: 'ID', value: dash(d.employeeId) },
        { label: '员工号', value: dash(d.employeeNo) },
        { label: '姓名', value: dash(d.name) },
        { label: '职务', value: dash(d.position) },
        { label: '等级', value: dash(d.level) },
        { label: '组织名称', value: dash(d.organizationName) }

      ]
    })
  }
})