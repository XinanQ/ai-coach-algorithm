const api = require('../../../api/index')
const MAX_ROUNDS = 3
const pad = n => (n < 10 ? '0' + n : '' + n)

Page({
  data: {
    taskId: '',
    scene: '存款推荐',
    messages: [],
    inputValue: '',
    round: 0,
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
    api.practice.startDialog(this.data.taskId).then((d) => {
      this.setData({ messages: d.messages, round: d.round })
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
    if (!text) return

    const messages = this.data.messages.concat([{ role: 'user', content: text }])
    // 实时评分随作答逐步上升（mock）
    const liveScore = Math.min(95, this.data.liveScore + 4)
    this.setData({ messages, inputValue: '', liveScore })

    if (this.data.round >= MAX_ROUNDS) {
      this.finishDialog()
      return
    }

    const nextRound = this.data.round + 1
    api.practice.replyDialog(this.data.taskId, text, nextRound).then((d) => {
      this.setData({
        messages: this.data.messages.concat([d.message]),
        round: d.round
      })
    })
  },
  finishDialog() {
    if (this._timer) clearInterval(this._timer)
    this.setData({ finished: true })
    wx.showLoading({ title: '正在评分...' })
    api.practice.finishDialog(this.data.taskId).then(() => {
      wx.hideLoading()
      wx.redirectTo({ url: `/pages/practice/result/result?taskId=${this.data.taskId}&score=${this.data.liveScore}` })
    }).catch(() => wx.hideLoading())
  }
})
