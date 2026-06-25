<template>
  <div class="page dashboard" v-loading="loading">
    <header class="page-header">
      <div>
        <h1>首页数据概览</h1>
        <p>{{ headerSubtitle }}</p>
      </div>
      <router-link class="button primary" :to="primaryAction.to">{{ primaryAction.label }}</router-link>
    </header>

    <template v-if="summary">
      <section class="grid grid-4 kpi-row">
        <el-card
          v-for="item in stats"
          :key="item.label"
          shadow="hover"
          class="kpi-card"
          :class="{ highlight: item.highlight }"
        >
          <div class="kpi-label">{{ item.label }}</div>
          <div class="kpi-value">{{ item.value }}</div>
          <div class="kpi-hint">{{ item.hint }}</div>
        </el-card>
      </section>

      <template v-if="isManager">
        <section class="dash-grid dash-2to1">
          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">进行中项目进度</span></template>
            <div v-if="projects.length" class="project-list">
              <div v-for="project in projects" :key="project.id" class="project-row">
                <div class="project-row-head">
                  <span class="project-name">{{ project.name }}</span>
                  <span class="project-rate">{{ formatRate(project.completionRate) }}</span>
                </div>
                <el-progress
                  :percentage="project.completionRate || 0"
                  :status="progressStatus(project.completionRate)"
                  :show-text="false"
                  :stroke-width="6"
                />
                <div class="project-meta" :class="{ urgent: isUrgent(project.daysToDeadline) }">
                  {{ deadlineText(project.daysToDeadline) }}
                </div>
              </div>
            </div>
            <el-empty v-else description="当前范围暂无进行中项目" :image-size="60" />
          </el-card>

          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">待办中心</span></template>
            <div class="todo-sub">待审核上报（{{ pendingReviewCount }}）</div>
            <div v-if="pendingReviews.length" class="todo-list">
              <router-link
                v-for="review in pendingReviews"
                :key="review.id"
                to="/performance-review"
                class="todo-row"
              >
                <span class="todo-text">
                  <span class="todo-main">{{ review.submitter || '—' }}<span v-if="review.result"> · {{ review.result }}</span></span>
                  <span v-if="review.reportDate" class="todo-date">{{ review.reportDate }}</span>
                </span>
                <span class="todo-arrow">→</span>
              </router-link>
              <router-link to="/performance-review" class="todo-more">查看全部待审核 →</router-link>
            </div>
            <el-empty v-else description="暂无待审核上报" :image-size="60" />
          </el-card>
        </section>

        <section class="grid grid-2">
          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">下属{{ subUnitLevelName }}业绩对比</span></template>
            <div v-if="subUnits.length" class="bar-list">
              <div v-for="unit in subUnits" :key="unit.name" class="bar-row">
                <span class="bar-label">{{ unit.name }}</span>
                <el-progress
                  class="bar-progress"
                  :percentage="barPercent(unit.points)"
                  :color="barColor(unit.points)"
                  :show-text="false"
                  :stroke-width="14"
                />
                <span class="bar-value">{{ round(unit.points) }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无下属单位数据" :image-size="60" />
          </el-card>

          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">积分排行榜 Top 5</span></template>
            <el-table :data="rankings" stripe size="small" empty-text="暂无排名数据">
              <el-table-column prop="rank" label="排名" width="64" align="center" />
              <el-table-column prop="name" label="人员" />
              <el-table-column prop="organization" label="机构" />
              <el-table-column label="积分" width="80" align="right">
                <template #default="{ row }"><span class="points">{{ round(row.points) }}</span></template>
              </el-table-column>
            </el-table>
          </el-card>
        </section>
      </template>

      <template v-else>
        <section class="grid grid-2">
          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">我的项目</span></template>
            <div v-if="projects.length" class="project-list">
              <div v-for="project in projects" :key="project.id" class="project-row">
                <div class="project-row-head">
                  <span class="project-name">{{ project.name }}</span>
                  <span class="project-rate">{{ formatRate(project.completionRate) }}</span>
                </div>
                <el-progress
                  :percentage="project.completionRate || 0"
                  :status="progressStatus(project.completionRate)"
                  :show-text="false"
                  :stroke-width="6"
                />
                <div class="project-meta" :class="{ urgent: isUrgent(project.daysToDeadline) }">
                  {{ deadlineText(project.daysToDeadline) }}
                </div>
              </div>
            </div>
            <el-empty v-else description="当前暂无可见项目" :image-size="60" />
          </el-card>

          <el-card shadow="hover" class="panel-card">
            <template #header><span class="panel-title">网点积分排行榜</span></template>
            <el-table :data="rankings" stripe size="small" empty-text="暂无排名数据">
              <el-table-column prop="rank" label="排名" width="64" align="center" />
              <el-table-column prop="name" label="人员" />
              <el-table-column prop="organization" label="机构" />
              <el-table-column label="积分" width="80" align="right">
                <template #default="{ row }"><span class="points">{{ round(row.points) }}</span></template>
              </el-table-column>
            </el-table>
          </el-card>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import { getDashboardSummary } from '../api/dashboard'

const currentUser = getCurrentUser() || {}
const loading = ref(true)
const summary = ref(null)

const isManager = computed(() => summary.value?.viewType === 'MANAGER')
const stats = computed(() => summary.value?.stats || [])
const projects = computed(() => summary.value?.projects || [])
const pendingReviews = computed(() => summary.value?.pendingReviews || [])
const pendingReviewCount = computed(() => summary.value?.pendingReviewCount || 0)
const subUnits = computed(() => summary.value?.subUnits || [])
const subUnitLevelName = computed(() => summary.value?.subUnitLevelName || '单位')
const rankings = computed(() => summary.value?.rankings || [])

const headerSubtitle = computed(() => {
  const role = currentUser.position || currentUser.roleName || '未设置职位'
  const org = summary.value?.organizationName || currentUser.organizationName || currentUser.organization || '未设置机构'
  const scope = currentUser.dataScope || '—'
  return `${role} · ${org}，数据范围：${scope}。`
})

const primaryAction = computed(() =>
  isManager.value
    ? { to: '/projects', label: '进入项目管理' }
    : { to: '/report', label: '进入每日上报' }
)

const maxSubUnitPoints = computed(() => {
  const values = subUnits.value.map((unit) => Number(unit.points) || 0)
  return Math.max(1, ...values)
})

function round(value) {
  if (value == null) return 0
  const num = Number(value)
  return Number.isFinite(num) ? Math.round(num) : 0
}

function formatRate(rate) {
  return rate == null ? '—' : `${rate}%`
}

function progressStatus(rate) {
  if (rate == null) return ''
  if (rate >= 80) return 'success'
  if (rate < 40) return 'exception'
  return 'warning'
}

function barPercent(points) {
  return Math.round(((Number(points) || 0) / maxSubUnitPoints.value) * 100)
}

function barColor(points) {
  const pct = barPercent(points)
  if (pct >= 70) return '#1d9e75'
  if (pct >= 40) return '#ef9f27'
  return '#e24b4a'
}

function isUrgent(days) {
  return days != null && days <= 2
}

function deadlineText(days) {
  if (days == null) return '未设置截止日期'
  if (days < 0) return `已逾期 ${-days} 天`
  if (days === 0) return '今日截止'
  return `距截止 ${days} 天`
}

onMounted(async () => {
  try {
    summary.value = await getDashboardSummary(currentUser)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.kpi-row {
  margin-bottom: 20px;
}

.kpi-card {
  text-align: left;
}

.kpi-card.highlight {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.kpi-label {
  font-size: 14px;
  color: #666;
}

.kpi-value {
  font-size: 32px;
  font-weight: 700;
  color: #0f766e;
  line-height: 1.3;
  margin-top: 4px;
}

.kpi-hint {
  font-size: 13px;
  color: #999;
  margin-top: 2px;
}

.dash-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.dash-2to1 {
  grid-template-columns: 1.4fr 1fr;
}

.panel-title {
  font-weight: 600;
  font-size: 16px;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.project-row-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 6px;
}

.project-rate {
  color: #666;
}

.project-meta {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.project-meta.urgent {
  color: #e24b4a;
}

.todo-sub {
  font-size: 13px;
  color: #666;
  margin-bottom: 10px;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.todo-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.todo-main {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todo-date {
  font-size: 12px;
  color: #999;
}

.todo-arrow {
  color: #0f766e;
  flex-shrink: 0;
}

.todo-more {
  font-size: 13px;
  color: #0f766e;
  text-decoration: none;
  margin-top: 2px;
}

.bar-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.bar-label {
  width: 76px;
  flex-shrink: 0;
}

.bar-progress {
  flex: 1;
}

.bar-value {
  width: 40px;
  text-align: right;
  color: #666;
}

.points {
  font-weight: 600;
  color: #0f766e;
}

@media (max-width: 900px) {
  .dash-2to1 {
    grid-template-columns: 1fr;
  }
}
</style>
