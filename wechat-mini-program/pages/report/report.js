const auth = require('../../utils/auth')
const api = require('../../api/index')

function today() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return date.getFullYear() + '-' + month + '-' + day
}

Page({
  data: {
    projects: [],
    projectIndex: -1,
    projectName: '请选择项目',
    indicators: [],
    indicatorIndex: -1,
    indicatorName: '请选择指标',
    amountLabel: '上报数量',
    reportDate: today(),
    amount: '',
    attachment: null,
    loading: false,
    submitting: false,
    blockedByRole: false,
    blockedText: ''
  },

  onShow() {
    if (!auth.requireLogin()) return

    this.refreshRoleAndOptions()
  },

  refreshRoleAndOptions() {
    const user = auth.getUserInfo() || {}
    const level = user.level || user.organizationLevel

    if (level) {
      this.applyRoleBlock(level)
      return
    }

    api.auth.getAccount()
      .then((account) => {
        const mergedUser = Object.assign({}, user, account)
        wx.setStorageSync('userInfo', mergedUser)
        this.applyRoleBlock(mergedUser.level || mergedUser.organizationLevel)
      })
      .catch(() => {
        this.applyRoleBlock(level)
      })
  },

  applyRoleBlock(level) {
    const blockedByRole = level === 'CITY' || level === 'BRANCH'
    this.setData({
      blockedByRole,
      blockedText: blockedByRole ? '市行和支行账号无需在小程序上报业绩，请在 Web 端审核员工上报。' : ''
    })

    if (!blockedByRole && this.data.projects.length === 0) {
      this.loadOptions()
    }
  },

  loadOptions() {
    this.setData({ loading: true })
    api.report.getReportOptions()
      .then((options) => {
        this.setData({
          projects: options.projects || [],
          loading: false
        })
      })
      .catch((err) => {
        this.setData({ loading: false })
        wx.showToast({ title: err.message || '加载项目失败', icon: 'none' })
      })
  },

  onProjectChange(e) {
    const projectIndex = Number(e.detail.value)
    const project = this.data.projects[projectIndex]

    this.setData({
      projectIndex,
      projectName: project ? project.name : '请选择项目',
      indicators: [],
      indicatorIndex: -1,
      indicatorName: '请选择指标',
      amountLabel: '上报数量'
    })

    if (!project) return

    api.report.getProjectIndicators(project.id)
      .then((indicators) => {
        this.setData({ indicators: indicators || [] })
      })
      .catch((err) => {
        wx.showToast({ title: err.message || '加载指标失败', icon: 'none' })
      })
  },

  onIndicatorChange(e) {
    const indicatorIndex = Number(e.detail.value)
    const indicator = this.data.indicators[indicatorIndex]
    this.setData({
      indicatorIndex,
      indicatorName: indicator ? indicator.name : '请选择指标',
      amountLabel: indicator && indicator.unit ? '上报数量（' + indicator.unit + '）' : '上报数量'
    })
  },

  onDateChange(e) {
    this.setData({ reportDate: e.detail.value })
  },

  onAmountInput(e) {
    this.setData({ amount: e.detail.value })
  },

  chooseAttachment() {
    wx.showActionSheet({
      itemList: ['选择图片', '选择文件'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.chooseImageAttachment()
        } else {
          this.chooseFileAttachment()
        }
      }
    })
  },

  chooseImageAttachment() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (!file) return
        this.setData({
          attachment: {
            path: file.tempFilePath,
            name: '图片凭证',
            type: 'image'
          }
        })
      }
    })
  },

  chooseFileAttachment() {
    if (!wx.chooseMessageFile) {
      wx.showToast({ title: '当前微信版本不支持选择文件', icon: 'none' })
      return
    }

    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (!file) return
        this.setData({
          attachment: {
            path: file.path,
            name: file.name || '附件凭证',
            type: 'file'
          }
        })
      }
    })
  },

  removeAttachment() {
    this.setData({ attachment: null })
  },

  submit() {
    if (this.data.blockedByRole) {
      wx.showToast({ title: '当前账号无需上报业绩', icon: 'none' })
      return
    }

    const project = this.data.projects[this.data.projectIndex]
    const indicator = this.data.indicators[this.data.indicatorIndex]
    const amount = Number(this.data.amount)

    if (!project) {
      wx.showToast({ title: '请选择项目', icon: 'none' })
      return
    }
    if (!indicator) {
      wx.showToast({ title: '请选择指标', icon: 'none' })
      return
    }
    if (!this.data.reportDate) {
      wx.showToast({ title: '请选择上报日期', icon: 'none' })
      return
    }
    if (!amount || amount <= 0) {
      wx.showToast({ title: '请输入大于 0 的上报数量', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    this.uploadThenSubmit(project, indicator)
  },

  uploadThenSubmit(project, indicator) {
    const user = auth.getUserInfo() || {}
    const attachment = this.data.attachment
    const uploadTask = attachment
      ? api.report.uploadAttachment(attachment.path)
      : Promise.resolve(null)

    uploadTask
      .then((uploaded) => {
        return api.report.submit({
          projectId: project.id,
          indicatorId: indicator.id,
          reportDate: this.data.reportDate,
          amount: this.data.amount,
          attachmentUrl: uploaded && uploaded.url,
          submitter: user.name,
          submitterId: user.employeeId,
          organizationId: user.organizationId
        })
      })
      .then(() => {
        wx.showToast({ title: '上报成功', icon: 'success' })
        this.setData({
          indicatorIndex: -1,
          amount: '',
          attachment: null,
          submitting: false
        })
      })
      .catch((err) => {
        this.setData({ submitting: false })
        wx.showToast({ title: err.message || '提交失败', icon: 'none' })
      })
  }
})
