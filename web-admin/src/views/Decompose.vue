<template>
  <div class="page">
    <p v-if="message" class="form-message-top" :class="{ danger: hasInvalidAllocation || messageError }">{{ message }}</p>

    <header class="page-header">
      <div>
        <h1>{{ isWorkbench ? '分解工作台' : '下发分解' }}</h1>
        <p>{{ headerDescription }}</p>
      </div>
      <button v-if="!activePlan?.readOnly" class="button primary" :disabled="!activePlan || saving" @click="saveDecompositionPlan">{{ saving ? '保存中…' : '保存分解' }}</button>
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
            <td>{{ planItem.project?.name || planItem.projectName || planItem.currentOrganization }}</td>
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
        <small>{{ activePlan.project?.name || activePlan.projectName || activePlan.currentOrganization }}</small>
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
          <Transition name="saved-fade">
            <small v-if="savedIndicatorIds.includes(summary.indicatorId)" class="saved-hint">✓ 已保存</small>
          </Transition>
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
    </section>

    <section v-else class="panel empty-state">
      <h2>暂无可分解项目</h2>
      <p>当前账号没有收到需要继续向下分解的项目任务。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCurrentUser } from '../auth/permissions'
import { resolveOrgId } from '../auth/orgScope'
import { buildPlanForProject, buildReceivedPlanForProject, getDecomposition, saveDecomposition } from '../api/decomposition'
import { getProject } from '../api/projects'

const route = useRoute()
const currentUser = getCurrentUser()
const plans = ref([])
const activePlanId = ref('')
const selectedIndicatorId = ref(null)
const message = ref('')
const messageError = ref(false)
const saving = ref(false)
// 保存成功后，在「指标余额」里命中的指标卡片上闪现「✓ 已保存」，几秒后自动淡出
const savedIndicatorIds = ref([])
let savedHintTimer = null

function flashSavedHints(ids) {
  if (savedHintTimer) clearTimeout(savedHintTimer)
  savedIndicatorIds.value = ids
  savedHintTimer = setTimeout(() => {
    savedIndicatorIds.value = []
    savedHintTimer = null
  }, 3000)
}

onBeforeUnmount(() => {
  if (savedHintTimer) clearTimeout(savedHintTimer)
})

// 记录加载时的分配基线（按 直属对象+指标 维度），用于判断本次到底改了哪些指标
let allocationBaseline = {}

function snapshotAllocations(plan) {
  const map = {}
  if (!plan) return map
  plan.targets.forEach((target) => {
    target.indicators.forEach((ind) => {
      map[`${target.id}:${ind.indicatorId}`] = Number(ind.currentAllocation || 0)
    })
  })
  return map
}

function changedIndicatorIds() {
  const plan = activePlan.value
  if (!plan) return []
  const changed = new Set()
  plan.targets.forEach((target) => {
    target.indicators.forEach((ind) => {
      const before = allocationBaseline[`${target.id}:${ind.indicatorId}`] ?? 0
      if (before !== Number(ind.currentAllocation || 0)) {
        changed.add(ind.indicatorId)
      }
    })
  })
  return [...changed]
}

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
    const defaultTotalTask = rows.reduce((sum, row) => sum + Number(row?.totalTask || 0), 0)
    const totalTask = activePlan.value.originType === 'received'
      ? Number(activePlan.value.receivedTotals?.find((item) => item.indicatorId === indicator.indicatorId)?.totalTask || defaultTotalTask)
      : defaultTotalTask
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
      progress: totalTask ? Math.min(100, Math.round((usedTotal / totalTask) * 100)) : 0
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
    const percent = activePlan.value.originType === 'received' && selectedSummary.totalTask
      ? Math.round((Number(row.currentAllocation || 0) / selectedSummary.totalTask) * 100)
      : row.totalTask ? Math.round((used / row.totalTask) * 100) : 0

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
  // 每次切换选中计划都重记基线，否则在工作台切到别的项目后，
  // 变更判断会拿旧项目的基线去比，导致未改动的指标被误判为「已保存」。
  allocationBaseline = snapshotAllocations(activePlan.value)
}

function sourceLabel(plan) {
  if (!plan) return ''
  return plan.originType === 'created' ? '本级创建' : plan.receivedFrom
}

// 工作台：把同一项目折叠成一条可编辑计划。只读的"上级下发收到记录"转成
// "继续向下分发"的可编辑计划；同项目已有可编辑记录则优先用它（与单项目路由逻辑一致）。
async function normalizeWorkbenchPlans(list) {
  const byProject = new Map()
  list.forEach((plan) => {
    const key = String(plan.projectId)
    const existing = byProject.get(key)
    if (!existing || (existing.readOnly && !plan.readOnly)) {
      byProject.set(key, plan)
    }
  })

  const normalized = []
  for (const plan of byProject.values()) {
    if (plan.originType === 'received' && plan.readOnly) {
      // 本机构是叶子（无直属下级）时 buildReceivedPlanForProject 返回 null，回退为只读查看
      const editable = await buildReceivedPlanForProject(plan.projectId, currentUser, plan)
      normalized.push(editable || plan)
    } else {
      normalized.push(plan)
    }
  }
  return normalized
}

async function loadDecomposition() {
  message.value = ''
  messageError.value = false
  savedIndicatorIds.value = []
  const projectId = route.params.id
  let result = await getDecomposition({
    projectId,
    role: currentUser?.role,
    organizationId: resolveOrgId(currentUser)
  })

  if (projectId) {
    if (result && result.originType === 'received' && result.readOnly) {
      // 上级下发、只读的收到记录 → 转成可编辑的"继续向下分发"计划（分配对象为本机构直属下级）
      const editable = await buildReceivedPlanForProject(projectId, currentUser, result)
      if (editable) result = editable
    } else if (!result) {
      // 本级创建但尚未分解过：按机构下属 + 项目指标动态生成可编辑计划
      result = await buildPlanForProject(projectId, currentUser)
    }
  }

  let list = Array.isArray(result) ? result : result ? [result] : []

  // 工作台（无 projectId）：每个项目折叠成一条可编辑计划，只读收到记录转可编辑
  if (!projectId && list.length) {
    list = await normalizeWorkbenchPlans(list)
  }

  // 后端 / 本地保存的记录不含 project 展示对象，补全项目名，避免渲染缺失（单项目与工作台都适用）
  if (list.some((plan) => !plan.project)) {
    const projectCache = new Map()
    for (const plan of list) {
      if (plan.project) continue
      const pid = plan.projectId ?? projectId
      if (pid == null) continue
      const key = String(pid)
      if (!projectCache.has(key)) {
        projectCache.set(key, await getProject(pid).catch(() => null))
      }
      const project = projectCache.get(key)
      if (project) {
        plan.project = project
        plan.projectName = project.name
      }
    }
  }

  plans.value = list
  // 重新加载后尽量保持当前选中的计划（如保存后刷新），找不到再退回第一个，
  // 避免在工作台里保存后选中项跳回列表第一个、提示错位。
  const keepActive = plans.value.some((plan) => plan.id === activePlanId.value)
  selectPlan(keepActive ? activePlanId.value : (plans.value[0]?.id || ''))
}

async function saveDecompositionPlan() {
  if (!activePlan.value || saving.value) return

  if (hasInvalidAllocation.value) {
    messageError.value = true
    message.value = '请先调整超分或负数的指标，再提交分解方案。'
    return
  }

  // 保存前先算出本次相对基线改动过的指标，成功后只在这些卡片上提示
  const changedIds = changedIndicatorIds()
  saving.value = true
  message.value = ''
  messageError.value = false

  try {
    const res = await saveDecomposition(activePlan.value)
    // 后端也可能返回 { success:false, message } 而不抛错，这里要如实反馈
    if (res && res.success === false) {
      messageError.value = true
      message.value = `保存失败：${res.message || res.error || '后端未接受本次分解'}`
      return
    }

    // 重新拉取，确保页面显示的是后端真正持久化的结果（loadDecomposition 会重置提示状态）
    await loadDecomposition()
    // 成功：只在本次改动过的指标卡片内闪现「✓ 已保存」
    flashSavedHints(changedIds)
    if (res && res.offline) {
      messageError.value = true
      message.value = '后端不可达，已本地暂存，恢复网络后请重新保存同步。'
    }
  } catch (e) {
    messageError.value = true
    message.value = `保存失败：${e.message || '请稍后重试'}`
  } finally {
    saving.value = false
  }
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

.form-message-top {
  margin: 0 0 16px;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid #0f766e;
  background: #f0fdfa;
  color: #0f766e;
  font-weight: 600;
}

.form-message-top.danger {
  border-left-color: #dc2626;
  background: #fee2e2;
  color: #b91c1c;
}

.saved-hint {
  color: #0f766e;
  font-weight: 600;
}

/* 「✓ 已保存」几秒后自动淡出 */
.saved-fade-leave-active {
  transition: opacity 0.6s ease;
}

.saved-fade-leave-to {
  opacity: 0;
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
