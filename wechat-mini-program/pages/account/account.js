const auth = require('../../utils/auth')
const api = require('../../api/index')

Page({
  data: {
    name: '',
    org: '',
    fields: []
  },
  onLoad() {
    if (!auth.requireLogin()) return
    this.loadProfile()
  },
  loadProfile() {
    // 规范个人信息接口 GET /api/mini/profile；失败回退本地登录态
    api.auth.getProfile()
      .then((d) => this.render(d))
      .catch(() => this.render(auth.getUserInfo() || {}))
  },
  render(d) {
    if (!d) return
    const dash = (v) => (v === undefined || v === null || v === '') ? '—' : v
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
