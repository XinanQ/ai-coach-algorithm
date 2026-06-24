<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>
      <router-link class="button" to="/dashboard">返回概览</router-link>
    </header>

    <section class="panel">
      <div v-if="canChangeLevel" class="ranking-tabs">
        <button
          v-for="tab in rankingTabs"
          :key="tab.id"
          type="button"
          @click="activeLevel = tab.id"
          :class="['ranking-tab', { active: activeLevel === tab.id }]"
        >
          {{ tab.name }}
        </button>
      </div>

      <div class="filter-panel">
        <p class="filter-title">筛选条件</p>
        <div class="filter-row">
          <label class="filter-item">
            <span class="filter-label">项目</span>
            <select v-model="filters.projectId" class="select" @change="onProjectChange">
              <option value="">全部项目</option>
              <option v-for="p in projects" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
            </select>
          </label>

          <label class="filter-item">
            <span class="filter-label">指标</span>
            <select v-model="filters.indicatorId" class="select" @change="loadRankings">
              <option value="">{{ indicatorAllLabel }}</option>
              <option v-for="ind in indicatorOptions" :key="ind.optionKey" :value="String(ind.id)">
                {{ ind.label }}
              </option>
            </select>
          </label>

          <label class="filter-item">
            <span class="filter-label">周期</span>
            <select v-model="filters.period" class="select" @change="loadRankings">
              <option value="DAY">日</option>
              <option value="WEEK">周</option>
              <option value="MONTH">月</option>
            </select>
          </label>

          <label class="filter-item">
            <span class="filter-label">日期</span>
            <input v-model="filters.date" class="field" type="date" @change="loadRankings" />
          </label>

          <button type="button" class="button primary query-btn" @click="loadRankings">查询排名</button>
        </div>

        <p class="filter-hint">{{ filterHint }}</p>

        <div class="filter-tags">
          <span class="tag" :class="{ active: !filters.projectId && !filters.indicatorId }">全部项目</span>
          <span class="tag" :class="{ active: !!filters.projectId && !filters.indicatorId }">整项目</span>
          <span class="tag" :class="{ active: !filters.projectId && !!filters.indicatorId }">跨项目单指标</span>
          <span class="tag" :class="{ active: !!filters.projectId && !!filters.indicatorId }">单项目单指标</span>
        </div>
      </div>

      <div class="ranking-header">
        <h2>{{ rankingTitle }} · {{ levelTitle }}</h2>
      </div>

      <div v-if="loading" class="no-data"><p>加载中…</p></div>
      <div v-else-if="rankingRows.length === 0" class="no-data">
        <p>暂无排名数据（需先有审核通过的上报并产生积分）</p>
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>排名</th>
            <th>{{ levelTitle }}</th>
            <th v-if="activeLevel === 'employee'">机构</th>
            <th>积分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rankingRows" :key="`${row.rank}-${row.id}`">
            <td>
              <span :class="['rank-badge', { 'top-3': row.rank <= 3 }]">{{ row.rank }}</span>
            </td>
            <td>{{ row.name }}</td>
            <td v-if="activeLevel === 'employee'">{{ row.organization }}</td>
            <td><strong>{{ row.points }}</strong></td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCurrentUser } from '../auth/permissions'
import { getProjects, getProjectIndicators, getIndicatorLibrary, getRankings } from '../api/rankings'

const projects = ref([])
const projectIndicators = ref([])
const indicatorLibrary = ref([])
const rankingRows = ref([])
const loading = ref(false)
const currentUser = getCurrentUser()
const route = useRoute()

const activeLevel = ref('employee')
const activeMode = ref('points')

const filters = reactive({
  projectId: '',
  indicatorId: '',
  period: 'MONTH',
  date: new Date().toISOString().slice(0, 10)
})

const allRankingTabs = [
  { id: 'employee', name: '员工层级' },
  { id: 'outlet', name: '网点层级' },
  { id: 'branch', name: '支行层级' },
  { id: 'city', name: '市行层级' }
]

const rankingTabs = computed(() => {
  if (currentUser?.role === 'employee') {
    return allRankingTabs.filter((tab) => tab.id === 'employee')
  }
  return allRankingTabs
})

const canChangeLevel = computed(() => currentUser?.role !== 'employee')

const levelTitle = computed(() => {
  const titles = { employee: '人员', outlet: '网点', branch: '支行', city: '市行' }
  return titles[activeLevel.value]
})

const pageTitle = computed(() => (activeMode.value === 'amount' ? '金额排名' : '积分排名'))

const pageDescription = computed(() => {
  return '项目、指标均可不选：不选项目=全部项目；选了项目但不选指标=整项目汇总'
})

const indicatorAllLabel = computed(() => {
  if (filters.projectId) return '整项目（汇总全部指标）'
  return '全部指标'
})

const indicatorOptions = computed(() => {
  if (filters.projectId) {
    return projectIndicators.value.map((ind) => ({
      id: ind.id,
      label: ind.name,
      optionKey: `p${filters.projectId}-i${ind.id}`
    }))
  }
  return indicatorLibrary.value.map((ind) => ({
    id: ind.id,
    label: ind.name,
    optionKey: `i${ind.id}`
  }))
})

const filterHint = computed(() => {
  const hasP = !!filters.projectId
  const hasI = !!filters.indicatorId
  if (!hasP && !hasI) return '当前：全部项目 + 全部指标加总'
  if (hasP && !hasI) return '当前：所选项目下全部指标加总（整项目排名）'
  if (!hasP && hasI) return '当前：全部项目下，所选指标加总'
  return '当前：所选项目 + 所选指标'
})

const rankingTitle = computed(() => {
  const p = projects.value.find((item) => String(item.id) === String(filters.projectId))
  const ind = indicatorOptions.value.find((item) => String(item.id) === String(filters.indicatorId))
  const parts = []
  parts.push(p ? p.name : '全部项目')
  parts.push(ind ? ind.label : filters.projectId ? '整项目' : '全部指标')
  return parts.join(' · ')
})

async function loadProjects() {
  projects.value = await getProjects()
}

async function loadIndicatorLibrary() {
  indicatorLibrary.value = await getIndicatorLibrary()
}

async function loadProjectIndicators() {
  if (!filters.projectId) {
    projectIndicators.value = []
    return
  }
  projectIndicators.value = await getProjectIndicators(filters.projectId)
}

async function onProjectChange() {
  filters.indicatorId = ''
  await loadProjectIndicators()
  await loadRankings()
}

async function loadRankings() {
  loading.value = true
  try {
    rankingRows.value = await getRankings(
      currentUser,
      activeLevel.value,
      filters.projectId,
      filters.indicatorId,
      { period: filters.period, date: filters.date }
    )
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (route.query.mode && ['points', 'amount'].includes(route.query.mode)) {
    activeMode.value = route.query.mode
  }
  await Promise.all([loadProjects(), loadIndicatorLibrary()])
  await loadRankings()
})

watch(activeLevel, () => loadRankings())
</script>

<style scoped>
.ranking-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
}

.ranking-tab {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  font-size: 14px;
}

.ranking-tab.active {
  background: #0f766e;
  border-color: #0f766e;
  color: #fff;
}

.filter-panel {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.filter-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 160px;
}

.filter-label {
  font-size: 13px;
  color: #6b7280;
}

.query-btn {
  height: 38px;
}

.filter-hint {
  margin: 12px 0 0;
  font-size: 13px;
  color: #0f766e;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.tag {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #e5e7eb;
  color: #6b7280;
}

.tag.active {
  background: #ccfbf1;
  color: #0f766e;
  font-weight: 600;
}

.ranking-header {
  margin-bottom: 16px;
}

.ranking-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f3f4f6;
  color: #6b7280;
  font-weight: 600;
  font-size: 13px;
}

.rank-badge.top-3 {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #fff;
}

.no-data {
  text-align: center;
  padding: 40px 20px;
  color: #6b7280;
}
</style>
