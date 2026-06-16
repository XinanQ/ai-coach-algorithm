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
          @click="activeLevel = tab.id"
          :class="['ranking-tab', { active: activeLevel === tab.id }]"
        >
          {{ tab.name }}
        </button>
      </div>

      <div class="toolbar">
        <select v-model="filters.indicator" class="select" @change="handleIndicatorChange">
          <option value="">全部任务</option>
          <option v-for="indicator in indicators" :key="indicator.id" :value="indicator.id">{{ indicator.name }}</option>
        </select>
      </div>

      <div v-if="!filters.indicator" class="indicator-grid">
        <div
          v-for="indicator in indicators"
          :key="indicator.id"
          @click="selectIndicator(indicator.id)"
          class="indicator-card"
        >
          <div class="indicator-header">
            <h3>{{ indicator.name }}</h3>
          </div>
          <div class="indicator-footer">
            <button class="view-btn">查看排名</button>
          </div>
        </div>
      </div>

      <div v-else>
        <div class="ranking-header">
          <h2>{{ currentIndicatorName }} - {{ levelTitle }}{{ modeTitle }}</h2>
          <button @click="backToAll" class="back-btn">返回全部任务</button>
        </div>

        <div v-if="filteredRankings.length === 0" class="no-data">
          <p>暂无排名数据</p>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>排名</th>
              <th>{{ levelTitle }}</th>
              <th v-if="activeLevel === 'employee'">机构</th>
              <th>完成量</th>
              <th>{{ activeMode === 'amount' ? '金额' : '积分' }}</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRankings" :key="row.rank">
              <td>
                <span :class="['rank-badge', { 'top-3': row.rank <= 3 }]">{{ row.rank }}</span>
              </td>
              <td>{{ row.name }}</td>
              <td v-if="activeLevel === 'employee'">{{ row.organization }}</td>
              <td>{{ row.achievement }}</td>
              <td><strong>{{ row.points }}</strong></td>
              <td><ProgressBar :value="row.completionRate" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ProgressBar from '../components/ProgressBar.vue'
import { getCurrentUser } from '../auth/permissions'
import { getRankingOptions, getRankings } from '../api/rankings'

const indicators = ref([])
const projects = ref([])
const rankingRows = ref([])
const currentUser = getCurrentUser()
const route = useRoute()

const activeLevel = ref('employee')
const activeMode = ref('points')

const allRankingTabs = [
  { id: 'employee', name: '员工层级' },
  { id: 'outlet', name: '网点层级' },
  { id: 'branch', name: '支行层级' },
  { id: 'city', name: '市行层级' }
]

const rankingTabs = computed(() => {
  if (currentUser?.role === 'employee') {
    return allRankingTabs.filter(tab => tab.id === 'employee')
  }
  return allRankingTabs
})

const filters = reactive({
  indicator: ''
})

const levelTitle = computed(() => {
  const titles = {
    employee: '人员',
    outlet: '网点',
    branch: '支行',
    city: '市行'
  }
  return titles[activeLevel.value]
})

const modeTitle = computed(() => {
  if (currentUser?.role !== 'city_admin') return ''
  return activeMode.value === 'amount' ? '（金额）' : ''
})

const pageTitle = computed(() => {
  if (activeMode.value === 'amount') return '金额排名'
  if (activeMode.value === 'points') return '积分排名'
  return '项目排名'
})

const pageDescription = computed(() => {
  const roleMap = {
    head_admin: '总行',
    province_admin: '省行',
    city_admin: '市行',
    branch_admin: '支行',
    outlet_admin: '网点',
    employee: '员工'
  }
  const roleLabel = roleMap[currentUser?.role] || '用户'
  const modeLabel = activeMode.value === 'amount' ? '金额' : '积分'
  return `您好，${roleLabel}，请查看${modeLabel}排名`
})

const currentIndicatorName = computed(() => {
  if (!filters.indicator) return ''
  const indicator = indicators.value.find(ind => String(ind.id) === String(filters.indicator))
  return indicator ? indicator.name : ''
})

const filteredRankings = computed(() => {
  return rankingRows.value
})

const selectIndicator = (indicatorId) => {
  filters.indicator = String(indicatorId)
  loadRankings()
}

const backToAll = () => {
  filters.indicator = ''
  loadRankings()
}

const handleIndicatorChange = () => {
  loadRankings()
}

const loadRankings = async () => {
  rankingRows.value = await getRankings(currentUser, activeLevel.value, '', filters.indicator, activeMode.value)
}

const loadOptionsAndData = async () => {
  const options = await getRankingOptions(currentUser, activeMode.value)
  projects.value = options.projects
  indicators.value = options.indicators
  loadRankings()
}

const canChangeLevel = computed(() => {
  return currentUser?.role !== 'employee'
})

onMounted(async () => {
  if (route.query.mode && ['points', 'amount'].includes(route.query.mode)) {
    activeMode.value = route.query.mode
  }
  loadOptionsAndData()
})

watch(activeLevel, () => {
  loadRankings()
})

watch(() => route.query.mode, (newMode) => {
  if (newMode && ['points', 'amount'].includes(newMode)) {
    activeMode.value = newMode
    filters.indicator = ''
    loadOptionsAndData()
  }
})
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
  transition: all 0.2s;
  font-size: 14px;
}

.ranking-tab:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.ranking-tab.active {
  background: #0f766e;
  border-color: #0f766e;
  color: #fff;
}

.ranking-tab:disabled {
  cursor: not-allowed;
  opacity: 1;
}

.indicator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.indicator-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  background: #fff;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.indicator-card:hover {
  border-color: #0f766e;
  box-shadow: 0 4px 12px rgba(15, 118, 110, 0.15);
  transform: translateY(-2px);
}

.indicator-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.indicator-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  line-height: 1.4;
}

.indicator-type {
  padding: 4px 8px;
  border-radius: 4px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 12px;
  font-weight: 500;
}

.indicator-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-item .label {
  color: #6b7280;
  font-size: 13px;
}

.info-item .value {
  color: #111827;
  font-size: 13px;
  font-weight: 500;
}

.indicator-footer {
  text-align: center;
}

.view-btn {
  width: 100%;
  padding: 8px 16px;
  border: 1px solid #0f766e;
  border-radius: 6px;
  background: #0f766e;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
}

.view-btn:hover {
  background: #0d655f;
  border-color: #0d655f;
}

.ranking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.ranking-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.back-btn {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.back-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
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
  box-shadow: 0 2px 4px rgba(251, 191, 36, 0.3);
}

.no-data {
  text-align: center;
  padding: 40px 20px;
  color: #6b7280;
}

.no-data p {
  font-size: 16px;
  margin: 0;
}
</style>
