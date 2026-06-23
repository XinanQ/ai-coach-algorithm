const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    templateId: '',
    name: '',
    level: 'must',
    targets: ['全部客户经理', '私行团队', '新员工'],
    targetIndex: 0,
    deadline: '',
    dims: [
      { label: '合规表达', checked: true },
      { label: '风险提示', checked: true },
      { label: '客户异议处理', checked: true },
      { label: '成交推进', checked: true }
    ]
  },
  onLoad(query) {
    if (!auth.requireLogin()) return
    const templateId = (query && query.templateId) || ''
    if (templateId) {
      this.setData({ templateId })
      // 从模板进入：拉模板详情预填任务名称与评分维度
      api.admin.getTemplateDetail(templateId).then((d) => {
        const dims = (d.dimensions || []).map((label) => ({ label, checked: true }))
        this.setData({
          name: d.name || this.data.name,
          dims: dims.length ? dims : this.data.dims
        })
      })
    }
  },
  onName(e) { this.setData({ name: e.detail.value }) },
  setLevel(e) { this.setData({ level: e.currentTarget.dataset.level }) },
  onTarget(e) { this.setData({ targetIndex: Number(e.detail.value) }) },
  onDeadline(e) { this.setData({ deadline: e.detail.value }) },
  toggleDim(e) {
    const i = e.currentTarget.dataset.index
    this.setData({ [`dims[${i}].checked`]: !this.data.dims[i].checked })
  },
  submit() {
    if (!this.data.name) {
      wx.showToast({ title: '请输入任务名称', icon: 'none' })
      return
    }
    if (!this.data.deadline) {
      wx.showToast({ title: '请选择截止时间', icon: 'none' })
      return
    }
    // body 对齐规范 POST /api/mini/admin/practice/tasks
    const payload = {
      templateId: this.data.templateId,
      name: this.data.name,
      level: this.data.level,
      targetPosition: this.data.targets[this.data.targetIndex],
      deadline: this.data.deadline,
      dimensions: this.data.dims.filter((d) => d.checked).map((d) => d.label)
    }
    api.admin.assignTask(payload).then(() => {
      wx.showToast({ title: '已下发', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 700)
    })
  }
})
