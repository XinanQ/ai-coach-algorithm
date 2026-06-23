const api = require('../../../api/index')
const pad = n => (n < 10 ? '0' + n : '' + n)

Page({
  data: {
    taskId: '',
    sessionId: '',
    scene: '存款推荐',
    messages: [],
    inputValue: '',
    round: 0,
    totalRounds: 3,
    finished: false,
    liveScore: 70,
    dims: ['风险揭示', '适当性匹配', '客户异议'],
    timeText: '00:00'
  },
  onLoad(query) {
    this.setData({ taskId: query.taskId || '' })
    this.startDialog()
    this.startTimer()
  },
  onUnload() {
    if (this._timer) clearInterval(this._timer)
  },
  startTimer() {
    let s = 0
    this._timer = setInterval(() => {
      s += 1
      this.setData({ timeText: `${pad(Math.floor(s / 60))}:${pad(s % 60)}` })
    }, 1000)
  },
  startDialog() {
    // 规范：start 返回 sessionId，后续 reply/finish 用它串联
    api.practice.startDialog(this.data.taskId).then((d) => {
      this.setData({
        sessionId: d.sessionId || '',
        messages: d.messages || [],
        round: d.round || 1,
        totalRounds: d.totalRounds || 3,
        liveScore: d.liveScore != null ? d.liveScore : this.data.liveScore
      })
    })
  },
  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },
  onVoice() {
    // 语音输入为前端演示，真实录音/转写需后端支持
    wx.showToast({ title: '语音为演示，请用文字回复', icon: 'none' })
  },
  send() {
    const text = this.data.inputValue.trim()
    if (!text || this.data.finished) return

    const messages = this.data.messages.concat([{ role: 'user', content: text }])
    this.setData({ messages, inputValue: '' })

    // 规范：reply 用 sessionId+text；实时分与是否结束以服务端返回为准
    api.practice.replyDialog(this.data.sessionId, text, this.data.round).then((d) => {
      const patch = {
        round: d.round != null ? d.round : this.data.round,
        liveScore: d.liveScore != null ? d.liveScore : this.data.liveScore
      }
      if (d.message) patch.messages = this.data.messages.concat([d.message])
      this.setData(patch)
      if (d.finished) this.finishDialog()
    })
  },
  finishDialog() {
    if (this.data.finished && this._finishing) return
    this._finishing = true
    if (this._timer) clearInterval(this._timer)
    this.setData({ finished: true })
    wx.showLoading({ title: '正在评分...' })
    // 规范：finish 用 sessionId，直接返回最终评分
    api.practice.finishDialog(this.data.sessionId).then((r) => {
      wx.hideLoading()
      const score = (r && r.score != null) ? r.score : this.data.liveScore
      wx.redirectTo({ url: `/pages/practice/result/result?taskId=${this.data.taskId}&score=${score}` })
    }).catch(() => wx.hideLoading())
  }
})
