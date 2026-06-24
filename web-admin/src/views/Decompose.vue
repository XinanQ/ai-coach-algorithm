<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>{{ isWorkbench ? '分解工作台' : '下发分解' }}</h1>
        <p>{{ headerDescription }}</p>
      </div>
      <button v-if="!activePlan?.readOnly" class="button primary" :disabled="!activePlan" @click="saveDecompositionPlan">保存分解</button>
      <span v-else class="badge neutral">上级下发 · 仅供查看</span>
    </header>

    <section v-if="isWorkbench && plans.length" class="panel">
      <div class="section-heading">
        <div>
          <h2>待处理项目池</h2>
          <p>工作台先汇总全部可分解项目，再进入单个项目做明细分配。</p>
        </div>
        <span class="badge neutral">{{ plans.length }} 个项目</span>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th>项目</th>
            <th>来源</th>
            <th>当前层级</th>
            <th>下发对象</th>
            <th>指标数</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="planItem in plans" :key="planItem.id" :class="{ 'active-row': planItem.id === activePlan?.id }">
            <td>{{ planItem.project.name }}</td>
            <td>{{ sourceLabel(planItem) }}</td>
            <td>{{ planItem.currentLevel }}</td>
            <td>{{ planItem.nextLevel }} · {{ planItem.targets.length }} 个</td>
            <td>{{ planItem.targets[0]?.indicators.length || 0 }}</td>
            <td><span class="badge">{{ planItem.status }}</span></td>
            <td>
              <button class="button" @click="selectPlan(planItem.id)">
                {{ planItem.readOnly ? '查看' : (planItem.id === activePlan?.id ? '正在编辑' : '进入分解') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="activePlan?.readOnly" class="panel readonly-banner">
      <strong>该任务由 {{ activePlan.receivedFrom }} 下发，仅供查看，不能修改分配。</strong>
    </section>

    <section v-if="activePlan" class="grid grid-4">
      <article class="stat-card">
        <span>{{ activePlan.originType === 'created' ? '项目属性' : '项目来源' }}</span>
        <strong>{{ sourceLabel(activePlan) }}</strong>
        <small>{{ activePlan.project.name }}</small>
      </article>
      <article class="stat-card">
        <span>当前层级</span>
        <strong>{{ activePlan.currentLevel }}</strong>
        <small>{{ activePlan.currentOrganization }}</small>
      </article>
      <article class="stat-card">
        <span>分配对象</span>
        <strong>{{ activePlan.nextLevel }}</strong>
        <small>{{ activePlan.targets.length }} 个直属对象</small>
      </article>
      <article class="stat-card">
        <span>校验状态</span>
        <strong :class="{ danger: hasInvalidAllocation }">{{ hasInvalidAllocation ? '需调整' : '可提交' }}</strong>
        <small>{{ hasInvalidAllocation ? '存在超分或负数' : '未超过当前可分配量' }}</small>
      </article>
    </section>

    <section v-if="activePlan" class="panel">
      <div class="section-heading">
        <div>
          <h2>指标余额</h2>
          <p>{{ activePlan.originType === 'created' ? '每个指标独立校验，本次下发不能超过总行设定任务。' : '每个指标独立校验，已分配 + 本次分配不能超过本级收到的任务。' }}</p>
        </div>
      </div>
      <div v-if="indicatorSummaries.length" class="indicator-grid">
        <button
          v-for="summary in indicatorSummaries"
          :key="summary.indicatorId"
          class="indicator-card"
          :class="{ active: summary.indicatorId === selectedIndicatorId, danger: summary.remaining < 0 }"
          @click="selectedIndicatorId = summary.indicatorId"
        >
          <span>{{ summary.indicator }}</span>
          <strong>{{ summary.currentTotal }} / {{ summary.totalTask }} {{ summary.unit }}</strong>
          <small>剩余 {{ summary.remaining }} {{ summary.unit }}</small>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${summary.progress}%` }"></div>
          </div>
        </button>
      </div>
      <p v-else class="muted">该项目尚未配置指标，请先完成指标配置后再下发分解。</p>
    </section>

    <section v-if="activePlan && indicatorSummaries.length" class="panel">
      <div class="section-heading">
        <div>
          <h2>{{ selectedSummary.indicator }} 分解</h2>
          <p>当前只展示选中指标，便于逐项录入和核对。</p>
        </div>
        <span class="badge" :class="{ danger: selectedSummary.remaining < 0 }">
          剩余 {{ selectedSummary.remaining }} {{ selectedSummary.unit }}
        </span>
      </div>

      <table class="table">
        <thead>
          <tr>
            <th>直属对象</th>
            <th>层级</th>
            <th>本级收到任务</th>
            <th>历史已分配</th>
            <th>本次下发</th>
            <th>下发后占比</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in visibleRows" :key="row.targetId">
            <td>{{ row.target }}</td>
            <td>{{ row.level }}</td>
            <td>{{ row.allocation.totalTask }} {{ row.allocation.unit }}</td>
            <td>{{ row.allocation.allocated }} {{ row.allocation.unit }}</td>
            <td>
              <input
                v-model.number="row.allocation.currentAllocation"
                class="field allocation-input"
                min="0"
                type="number"
                :disabled="activePlan.readOnly"
              />
              {{ row.allocation.unit }}
            </td>
            <td>{{ row.percent }}%</td>
          </tr>
        </tbody>
      </table>
      <p v-if="message" class="form-message" :class="{ danger: hasInvalidAllocation }">{{ message }}</p>
    </section>

    <section v-else class="panel empty-state">
      <h2>暂无可分解项目</h2>
      <p>当前账号没有收到需要继续向下分解的项目任务。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCurrentUser } from '../auth/permissions'
import { resolveOrgId } from '../auth/orgScope'
import { buildPlanForProject, getDecomposition, saveDecomposition } from '../api/decomposition'

const route = useRoute()
const currentUser = getCurrentUser()
const plans = ref([])
const activePlanId = ref('')
const selectedIndicatorId = ref(null)
const message = ref('')

const isWorkbench = computed(() => !route.params.id)
const activePlan = computed(() => plans.value.find((plan) => plan.id === activePlanId.value) || null)
const headerDescription = computed(() => {
  if (!activePlan.value) {
    return `${currentUser?.organization || '当前机构'} 暂无可继续下发的项目任务。`
  }

  if (activePlan.value.originType === 'created') {
    return `${activePlan.value.currentOrganization} 创建项目后，可直接向直属${activePlan.value.nextLevel}下发指标。`
  }

  return `${activePlan.value.currentOrganization} 承接 ${sourceLabel(activePlan.value)} 下发的任务后，只能继续分配给直属${activePlan.value.nextLevel}。`
})

const indicatorSummaries = computed(() => {
  if (!activePlan.value) return []

  const indicators = activePlan.value.targets[0]?.indicators || []
  return indicators.map((indicator) => {
    const rows = activePlan.value.targets.map((target) =>
      target.indicators.find((item) => item.indicatorId === indicator.indicatorId)
    )
    const currentTotal = rows.reduce((sum, row) => sum + Number(row?.currentAllocation || 0), 0)
    const allocatedTotal = rows.reduce((sum, row) => sum + Number(row?.allocated || 0), 0)
    const totalTask = rows.reduce((sum, row) => sum + Number(row?.totalTask || 0), 0)
    const usedTotal = allocatedTotal + currentTotal
    const remaining = totalTask - usedTotal

    return {
      indicatorId: indicator.indicatorId,
      indicator: indicator.indicator,
      unit: indicator.unit,
      totalTask,
      allocatedTotal,
      currentTotal,
      remaining,
      progress: Math.min(100, Math.round((usedTotal / totalTask) * 100))
    }
  })
})

const selectedSummary = computed(
  () => indicatorSummaries.value.find((summary) => summary.indicatorId === selectedIndicatorId.value) || {}
)

const visibleRows = computed(() => {
  if (!activePlan.value || !selectedIndicatorId.value) return []

  return activePlan.value.targets.map((target) => {
    const row = target.indicators.find((item) => item.indicatorId === selectedIndicatorId.value)
    const used = Number(row.allocated || 0) + Number(row.currentAllocation || 0)
    const percent = row.totalTask ? Math.round((used / row.totalTask) * 100) : 0

    return {
      targetId: target.id,
      target: target.target,
      level: target.level,
      allocation: row,
      percent
    }
  })
})

const hasInvalidAllocation = computed(() => {
  const hasNegative = activePlan.value?.targets.some((target) =>
    target.indicators.some((indicator) => Number(indicator.currentAllocation || 0) < 0)
  )
  return Boolean(hasNegative || indicatorSummaries.value.some((summary) => summary.remaining < 0))
})

function selectPlan(planId) {
  activePlanId.value = planId
  selectedIndicatorId.value = indicatorSummaries.value[0]?.indicatorId || null
  message.value = ''
}

function sourceLabel(plan) {
  if (!plan) return ''
  return plan.originType === 'created' ? '本级创建' : plan.receivedFrom
}

async function loadDecomposition() {
  message.value = ''
  const projectId = route.params.id
  let result = await getDecomposition({
    projectId,
    role: currentUser?.role,
    organizationId: resolveOrgId(currentUser)
  })

  // 后端项目在 mock 中没有预置分解计划时，按机构下属 + 项目指标动态生成
  if (!result && projectId) {
    result = await buildPlanForProject(projectId, currentUser)
  }

  plans.value = Array.isArray(result) ? result : result ? [result] : []
  selectPlan(plans.value[0]?.id || '')
}

async function saveDecompositionPlan() {
  if (!activePlan.value) return

  if (hasInvalidAllocation.value) {
    message.value = '请先调整超分或负数的指标，再提交分解方案。'
    return
  }

  await saveDecomposition(activePlan.value)
  message.value = `已保存 ${activePlan.value.currentOrganization} 到直属${activePlan.value.nextLevel}的分解方案。`
}

onMounted(loadDecomposition)
watch(() => route.params.id, loadDecomposition)
</script>

<style scoped>
.indicator-card {
  text-align: left;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  cursor: pointer;
}

.indicator-card small,
.section-heading p {
  color: #6b7280;
  font-size: 13px;
}

.indicator-card.active {
  border-color: #0f766e;
  box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.12);
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.section-heading h2 {
  margin: 0 0 4px;
}

.active-row {
  background: #f0fdfa;
}

.indicator-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.indicator-card {
  display: grid;
  gap: 8px;
  padding: 14px;
}

.indicator-card strong {
  color: #111827;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5e7eb;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: #0f766e;
}

.allocation-input {
  width: 120px;
}

.readonly-banner {
  border-left: 4px solid #f59e0b;
  background: #fffbeb;
  color: #92400e;
}

.form-message {
  margin-top: 14px;
  color: #0f766e;
}

.danger {
  color: #dc2626;
}

.badge.danger {
  background: #fee2e2;
}

.indicator-card.danger {
  border-color: #fca5a5;
}

.indicator-card.danger .progress-fill {
  background: #dc2626;
}

.empty-state {
  display: grid;
  gap: 6px;
}

@media (max-width: 900px) {
  .indicator-grid {
    grid-template-columns: 1fr;
  }

  .section-heading {
    display: grid;
  }
}
</style>
