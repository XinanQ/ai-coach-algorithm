const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    team: {},
    completionTop3: [],
    abilityTop3: []
  },
  onShow() {
    if (!auth.guard('manager')) return
    this.loadData()
  },
  loadData() {
    api.admin.getAnalysis().then((d) => {
      const max = Math.max.apply(null, d.abilityTop3.map((a) => a.count))
      const abilityTop3 = d.abilityTop3.map((a) => ({
        name: a.name,
        count: a.count,
        pct: max > 0 ? Math.round((a.count / max) * 100) : 0
      }))
      this.setData({
        team: d.team,
        completionTop3: d.completionTop3,
        abilityTop3
      })
    })
  }
})
