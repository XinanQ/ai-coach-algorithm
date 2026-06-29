const auth = require('../../../utils/auth')
const api = require('../../../api/index')

Page({
  data: {
    scripts: [],
    visibleScripts: [],
    categories: [],
    activeCategory: '',
    keyword: ''
  },
  onShow() {
    if (!auth.guard('staff')) return
    api.script.getList().then((scripts) => {
      const normalized = (scripts || []).map((item) => Object.assign({}, item, {
        displayTitle: item.title || item.chunkId || item.scriptId || '',
        category: item.businessName || item.scene || ''
      }))
      const categories = Array.from(new Set(
        normalized.map((item) => item.category).filter(Boolean)
      ))
      this.setData({ scripts: normalized, categories }, () => this.applyFilters())
    })
  },
  onKeywordInput(e) {
    this.setData({ keyword: (e.detail.value || '').trim() }, () => this.applyFilters())
  },
  selectCategory(e) {
    this.setData({ activeCategory: e.currentTarget.dataset.category || '' }, () => this.applyFilters())
  },
  applyFilters() {
    const keyword = this.data.keyword.toLowerCase()
    const activeCategory = this.data.activeCategory
    const visibleScripts = this.data.scripts.filter((item) => {
      if (activeCategory && item.category !== activeCategory) return false
      if (!keyword) return true
      const searchable = [
        item.title,
        item.scene,
        item.businessName,
        item.sourceName
      ].filter(Boolean).join(' ').toLowerCase()
      return searchable.includes(keyword)
    })
    this.setData({ visibleScripts })
  },
  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/script/detail/detail?id=${id}` })
  }
})
