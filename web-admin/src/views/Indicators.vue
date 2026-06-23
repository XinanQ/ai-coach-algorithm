<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>指标配置</h1>
        <p>{{ project.name }} · 当前账号{{ canEdit ? '可维护指标' : '仅可查看指标' }}。</p>
      </div>
      <button class="button primary" :disabled="!canEdit" @click="startCreate">新增指标</button>
    </header>

    <section class="grid grid-4">
      <article class="stat-card">
        <span>指标数量</span>
        <strong>{{ projectIndicators.length }}</strong>
        <small>{{ resultIndicatorCount }} 个结果指标</small>
      </article>
      <article class="stat-card">
        <span>权重合计</span>
        <strong :class="{ danger: totalWeight !== 100 }">{{ totalWeight }}%</strong>
        <small>{{ totalWeight === 100 ? '权重已配平' : '建议调整至 100%' }}</small>
      </article>
      <article class="stat-card">
        <span>大单奖指标</span>
        <strong>{{ bigOrderCount }}</strong>
        <small>已设置起征点</small>
      </article>
      <article class="stat-card">
        <span>配置权限</span>
        <strong>{{ canEdit ? '可编辑' : '只读' }}</strong>
        <small>{{ currentUser.organization }}</small>
      </article>
    </section>

    <section v-if="!canEdit" class="panel readonly-panel">
      <strong>当前机构不是项目创建机构</strong>
      <span>你可以查看指标规则，但只有项目归属机构的管理员可以新增、编辑和删除指标。</span>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>指标清单</h2>
          <p>过程指标用于日常触达，结果指标参与积分和排名。</p>
        </div>
        <span class="badge" :class="{ danger: totalWeight !== 100 }">权重 {{ totalWeight }}%</span>
      </div>

      <table class="table">
        <thead>
          <tr>
            <th>指标名称</th>
            <th>指标类型</th>
            <th>数值类型</th>
            <th>单位</th>
            <th>占比</th>
            <th>积分标准</th>
            <th>大单奖</th>
            <th>达人数量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody v-if="projectIndicators.length">
          <tr v-for="indicator in projectIndicators" :key="indicator.id">
            <td>{{ indicator.name }}</td>
            <td><span class="badge">{{ indicator.indicatorType }}</span></td>
            <td>{{ indicator.valueType }}</td>
            <td>{{ indicator.unit }}</td>
            <td>{{ indicator.weight }}%</td>
            <td>{{ indicator.pointRule }} 分 / {{ indicator.unit }}</td>
            <td>{{ indicator.bigOrderEnabled ? `${indicator.bigOrderThreshold} ${indicator.unit}` : '未设置' }}</td>
            <td>{{ indicator.talentCount }}</td>
            <td>
              <button class="button" :disabled="!canEdit" @click="startEdit(indicator)">编辑</button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="9" class="muted">当前项目尚未配置指标。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="canEdit" class="panel">
      <div class="section-heading">
        <div>
          <h2>{{ editingId ? '编辑指标' : '新增指标' }}</h2>
          <p>保存后会更新本页配置，后续接入后端时替换为保存接口。</p>
        </div>
        <button v-if="editingId" class="button" @click="resetForm">取消编辑</button>
      </div>

      <div class="form-grid">
        <label class="form-field">
          指标名称
          <input v-model.trim="form.name" class="field" placeholder="例如：定期存款" />
        </label>
        <label class="form-field">
          指标类型
          <select v-model="form.indicatorType" class="select">
            <option>过程指标</option>
            <option>结果指标</option>
          </select>
        </label>
        <label class="form-field">
          数值类型
          <select v-model="form.valueType" class="select">
            <option>金额</option>
            <option>数量</option>
          </select>
        </label>
        <label class="form-field">
          单位
          <input v-model.trim="form.unit" class="field" placeholder="万元 / 户 / 次" />
        </label>
        <label class="form-field">
          占比
          <input v-model.number="form.weight" class="field" type="number" min="0" max="100" />
        </label>
        <label class="form-field">
          积分标准
          <input v-model.number="form.pointRule" class="field" type="number" min="0" step="0.1" />
        </label>
        <label class="form-field">
          达人数量
          <input v-model.number="form.talentCount" class="field" type="number" min="0" />
        </label>
        <label class="form-field switch-field">
          大单奖
          <input v-model="form.bigOrderEnabled" type="checkbox" />
        </label>
        <label class="form-field">
          大单奖起征点
          <input
            v-model.number="form.bigOrderThreshold"
            class="field"
            type="number"
            min="0"
            :disabled="!form.bigOrderEnabled"
          />
        </label>
      </div>

      <div class="form-actions">
        <button class="button primary" @click="saveIndicator">{{ editingId ? '保存修改' : '添加指标' }}</button>
        <p v-if="message" class="form-message" :class="{ danger: messageType === 'error' }">{{ message }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCurrentUser } from '../auth/permissions'
import { getProject } from '../api/projects'
import { getIndicators } from '../api/indicators'

const route = useRoute()
const currentUser = getCurrentUser()
const project = ref({})
const projectIndicators = ref([])
const editingId = ref(null)
const message = ref('')
const messageType = ref('success')

const form = reactive({
  name: '',
  indicatorType: '结果指标',
  valueType: '金额',
  unit: '万元',
  weight: 0,
  pointRule: 0,
  bigOrderEnabled: false,
  bigOrderThreshold: 0,
  talentCount: 0
})

const canEdit = computed(() =>
    Number(project.value.organizationId) === Number(currentUser?.organizationId)
)
const totalWeight = computed(() =>
  projectIndicators.value.reduce((sum, indicator) => sum + Number(indicator.weight || 0), 0)
)
const resultIndicatorCount = computed(
  () => projectIndicators.value.filter((indicator) => indicator.indicatorType === '结果指标').length
)
const bigOrderCount = computed(
  () => projectIndicators.value.filter((indicator) => indicator.bigOrderEnabled).length
)

function resetForm({ keepMessage = false } = {}) {
  editingId.value = null
  Object.assign(form, {
    name: '',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 0,
    pointRule: 0,
    bigOrderEnabled: false,
    bigOrderThreshold: 0,
    talentCount: 0
  })
  if (!keepMessage) message.value = ''
}

function startCreate() {
  resetForm({ keepMessage: true })
}

function startEdit(indicator) {
  editingId.value = indicator.id
  Object.assign(form, {
    name: indicator.name,
    indicatorType: indicator.indicatorType,
    valueType: indicator.valueType,
    unit: indicator.unit,
    weight: indicator.weight,
    pointRule: indicator.pointRule,
    bigOrderEnabled: indicator.bigOrderEnabled,
    bigOrderThreshold: indicator.bigOrderThreshold,
    talentCount: indicator.talentCount
  })
  message.value = ''
}

function validateForm() {
  if (!form.name) return '指标名称不能为空。'
  if (!form.unit) return '单位不能为空。'
  if (Number(form.weight) <= 0 || Number(form.weight) > 100) return '占比必须在 1 到 100 之间。'
  if (Number(form.pointRule) <= 0) return '积分标准必须大于 0。'
  if (Number(form.talentCount) < 0) return '达人数量不能为负数。'
  if (form.bigOrderEnabled && Number(form.bigOrderThreshold) <= 0) return '启用大单奖时必须设置起征点。'
  return ''
}

function saveIndicator() {
  const error = validateForm()
  if (error) {
    message.value = error
    messageType.value = 'error'
    return
  }

  const payload = {
    ...form,
    id: editingId.value || Date.now(),
    projectId: route.params.id,
    bigOrderThreshold: form.bigOrderEnabled ? Number(form.bigOrderThreshold) : 0
  }

  if (editingId.value) {
    projectIndicators.value = projectIndicators.value.map((indicator) =>
      indicator.id === editingId.value ? payload : indicator
    )
  } else {
    projectIndicators.value = [...projectIndicators.value, payload]
  }

  message.value = totalWeight.value === 100 ? '指标配置已更新。' : '指标配置已更新，请继续调整权重至 100%。'
  messageType.value = totalWeight.value === 100 ? 'success' : 'error'
  resetForm()
}

async function loadPage() {
  project.value = await getProject(route.params.id)
  projectIndicators.value = await getIndicators(route.params.id)
  resetForm()
}

onMounted(loadPage)
watch(() => route.params.id, loadPage)
</script>

<style scoped>
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

.section-heading p {
  color: #6b7280;
  font-size: 13px;
}

.readonly-panel {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: #374151;
  background: #f9fafb;
}

.switch-field {
  display: flex;
  min-height: 36px;
  align-items: center;
  justify-content: space-between;
}

.switch-field input {
  width: 18px;
  height: 18px;
}

.form-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
}

.form-message {
  margin: 0;
  color: #0f766e;
}

.danger {
  color: #dc2626;
}

.badge.danger {
  background: #fee2e2;
}

@media (max-width: 900px) {
  .section-heading,
  .readonly-panel,
  .form-actions {
    display: grid;
  }
}
</style>
