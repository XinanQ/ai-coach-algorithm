<template>
  <div class="page employee-crud-page">
    <header class="page-header">
      <div>
        <h1>人员管理</h1>
        <p>新增、编辑、删除和查询员工信息。</p>
      </div>
      <button class="button primary" type="button" @click="openAddDialog">+ 新增人员</button>
    </header>

    <section class="panel toolbar">
      <input
        v-model="searchKeyword"
        type="text"
        class="field search-field"
        placeholder="搜索姓名、邮箱..."
        style="max-width: 260px"
      />
      <select v-model="filterOrg" class="select">
        <option value="">全部机构</option>
        <option v-for="org in orgOptions" :key="org" :value="org">{{ org }}</option>
      </select>
      <select v-model="filterWorkType" class="select">
        <option value="">内勤/外勤</option>
        <option value="内勤">内勤</option>
        <option value="外勤">外勤</option>
      </select>
      <select v-model="filterIsAdmin" class="select">
        <option value="">全部权限</option>
        <option value="true">管理员</option>
        <option value="false">普通员工</option>
      </select>
      <span class="result-count">共 {{ filteredEmployees.length }} 条</span>
    </section>

    <section class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>姓名</th>
            <th>邮箱</th>
            <th>职务</th>
            <th>所属机构</th>
            <th>员工类型</th>
            <th>权限</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(emp, index) in filteredEmployees" :key="emp.id">
            <td>{{ startIndex + index + 1 }}</td>
            <td><strong>{{ emp.name }}</strong></td>
            <td>{{ emp.email }}</td>
            <td>{{ emp.position || '—' }}</td>
            <td>{{ emp.organization }}</td>
            <td>{{ emp.workType || '—' }} · {{ emp.isNew ? '新员工' : '非新' }}</td>
            <td>
              <span :class="['badge', emp.isAdmin ? 'badge-admin' : 'badge-normal']">
                {{ emp.isAdmin ? '管理员' : '普通员工' }}
              </span>
            </td>
            <td class="action-cell">
              <button class="btn-sm btn-edit" type="button" @click="openEditDialog(emp)">编辑</button>
              <button class="btn-sm btn-delete" type="button" @click="confirmDelete(emp)">删除</button>
            </td>
          </tr>
          <tr v-if="!filteredEmployees.length">
            <td colspan="8" class="empty-row">暂无数据</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="pagination-bar">
        <button class="btn-page" type="button" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="btn-page" type="button" :disabled="currentPage === totalPages" @click="currentPage++">下一页</button>
      </div>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑人员' : '新增人员'"
      width="580px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="!isEditing" class="upload-area">
        <p class="upload-tip">或从本地文件批量导入（支持 .csv / .tsv / .txt）</p>
        <div
          class="drop-zone"
          :class="{ 'drop-active': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="handleFileDrop"
          @click="$refs.fileInput?.click()"
        >
          <input ref="fileInput" type="file" accept=".csv,.tsv,.txt" class="hidden-input" @change="handleFileSelect" />
          <span class="drop-icon">{{ isDragOver ? '📥' : '📄' }}</span>
          <p>{{ isDragOver ? '松开以上传' : '拖拽文件到此处，或点击选择' }}</p>
          <span class="drop-hint">CSV 格式：姓名,邮箱,职务,所属机构,员工类型,是否管理员</span>
        </div>
        <div v-if="uploadPreview.length" class="preview-box">
          <p class="preview-title">已解析 {{ uploadPreview.length }} 条记录：</p>
          <table class="preview-table">
            <thead>
              <tr><th>#</th><th>姓名</th><th>邮箱</th><th>机构</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in uploadPreview" :key="i" :class="{ 'row-invalid': !row._valid }">
                <td>{{ i + 1 }}</td>
                <td>{{ row.name || '<空>' }}</td>
                <td>{{ row.email || '<空>' }}</td>
                <td>{{ row.organization || '<空>' }}</td>
                <td>{{ row._valid ? '✓' : '✗ 缺少必填项' }}</td>
              </tr>
            </tbody>
          </table>
          <div class="preview-actions">
            <button class="button primary btn-sm" type="button" @click="confirmBatchImport">确认导入全部</button>
            <button class="button secondary btn-sm" type="button" @click="clearUpload">清除</button>
          </div>
        </div>
      </div>

      <form class="employee-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 姓名</label>
          <input v-model="formData.name" type="text" class="field" placeholder="请输入姓名" required />
        </div>
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 邮箱</label>
          <input v-model="formData.email" type="email" class="field" placeholder="请输入邮箱" required />
        </div>
        <div class="form-group">
          <label class="form-label">职务</label>
          <input v-model="formData.position" type="text" class="field" placeholder="如：客户经理、柜员" />
        </div>
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 所属机构</label>
          <input v-model="formData.organization" type="text" class="field" placeholder="如：南京市行鼓楼支行" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">员工类型</label>
            <select v-model="formData.workType" class="field select-field">
              <option value="">请选择</option>
              <option value="内勤">内勤</option>
              <option value="外勤">外勤</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">是否管理员</label>
            <select v-model="formData.isAdmin" class="field select-field">
              <option :value="false">否</option>
              <option :value="true">是</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">是否新员工</label>
          <select v-model="formData.isNew" class="field select-field">
            <option :value="false">否</option>
            <option :value="true">是</option>
          </select>
        </div>
      </form>

      <template #footer>
        <button class="button secondary" type="button" @click="dialogVisible = false">取消</button>
        <button class="button primary" type="button" :disabled="!formValid" @click="handleSubmit">
          {{ isEditing ? '保存修改' : '确认新增' }}
        </button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="deleteConfirmVisible"
      title="确认删除"
      width="400px"
    >
      <p class="delete-confirm-text">
        确定要删除员工 <strong>{{ deleteTarget?.name }}</strong> 吗？此操作不可撤销。
      </p>
      <template #footer>
        <button class="button secondary" type="button" @click="deleteConfirmVisible = false">取消</button>
        <button class="button danger" type="button" @click="handleDelete">确认删除</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElDialog } from 'element-plus'

const STORAGE_KEY = 'employee_crud_data'

const DEFAULT_EMPLOYEES = [
  {
    id: 'emp-001',
    name: '张三',
    email: 'zhangsan@bank.com',
    position: '客户经理',
    organization: '南京市行鼓楼支行',
    workType: '外勤',
    isNew: true,
    isAdmin: false,
    createdAt: Date.now() - 86400000 * 30
  },
  {
    id: 'emp-002',
    name: '李四',
    email: 'lisi@bank.com',
    position: '柜员',
    organization: '南京市行玄武支行',
    workType: '内勤',
    isNew: false,
    isAdmin: true,
    createdAt: Date.now() - 86400000 * 20
  },
  {
    id: 'emp-003',
    name: '王五',
    email: 'wangwu@bank.com',
    position: '信贷专员',
    organization: '南京市行秦淮支行',
    workType: '外勤',
    isNew: true,
    isAdmin: false,
    createdAt: Date.now() - 86400000 * 10
  }
]

const employees = ref([])
const searchKeyword = ref('')
const filterOrg = ref('')
const filterWorkType = ref('')
const filterIsAdmin = ref('')
const currentPage = ref(1)
const pageSize = 10

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const formData = reactive({
  name: '',
  email: '',
  position: '',
  organization: '',
  workType: '',
  isAdmin: false,
  isNew: true
})

const deleteConfirmVisible = ref(false)
const deleteTarget = ref(null)

const isDragOver = ref(false)
const uploadPreview = ref([])

function parseCSV(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return []

  const delimiter = lines[0].includes('\t') ? '\t' : ','
  const headers = lines[0].split(delimiter).map((h) => h.trim().replace(/^["']|["']$/g, ''))

  const nameIdx = headers.findIndex((h) => h === '姓名' || h.toLowerCase() === 'name')
  const emailIdx = headers.findIndex((h) => h === '邮箱' || h.toLowerCase() === 'email')
  const posIdx = headers.findIndex((h) => h === '职务' || h === 'position')
  const orgIdx = headers.findIndex((h) => h === '所属机构' || h === 'organization' || h === 'organizationName')
  const typeIdx = headers.findIndex((h) => h === '员工类型' || h === 'workType')
  const adminIdx = headers.findIndex((h) => h === '是否管理员' || h === 'isAdmin')

  const rows = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(delimiter).map((c) => c.trim().replace(/^["']|["']$/g, ''))
    const name = nameIdx >= 0 ? (cols[nameIdx] || '').trim() : ''
    const email = emailIdx >= 0 ? (cols[emailIdx] || '').trim() : ''
    const organization = orgIdx >= 0 ? (cols[orgIdx] || '').trim() : ''
    const _valid = !!(name && email && organization)

    rows.push({
      name,
      email,
      position: posIdx >= 0 ? (cols[posIdx] || '').trim() : '',
      organization,
      workType: normalizeType(typeIdx >= 0 ? (cols[typeIdx] || '').trim() : ''),
      isAdmin: parseAdmin(adminIdx >= 0 ? cols[adminIdx] : ''),
      _valid
    })
  }
  return rows
}

function normalizeType(val) {
  const s = String(val || '').trim()
  if (!s) return ''
  if (s.includes('内勤')) return '内勤'
  if (s.includes('外勤')) return '外勤'
  return s
}

function parseAdmin(val) {
  if (val === true || val === false) return val
  const s = String(val || '').trim()
  if (['true', '是', '1', 'yes', 'y'].includes(s)) return true
  if (['false', '否', '0', 'no', 'n'].includes(s)) return false
  return false
}

function handleFileDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) processFile(file)
}

function handleFileSelect(e) {
  const file = e.target?.files?.[0]
  if (file) processFile(file)
}

function processFile(file) {
  uploadPreview.value = []
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      const text = ev.target.result
      uploadPreview.value = parseCSV(text)
      if (!uploadPreview.value.length) {
        alert('文件内容为空或格式不正确，请确保首行为表头，后续为数据行。')
      }
    } catch (err) {
      alert('文件解析失败：' + err.message)
    }
  }
  reader.readAsText(file, 'UTF-8')
}

function confirmBatchImport() {
  const validRows = uploadPreview.value.filter((r) => r._valid)
  if (!validRows.length) {
    alert('没有有效数据可导入，请检查必填字段（姓名、邮箱、所属机构）。')
    return
  }

  const now = Date.now()
  const newEmps = validRows.map((r, idx) => ({
    id: `emp-batch-${now}-${idx}`,
    name: r.name,
    email: r.email,
    position: r.position || '',
    organization: r.organization,
    workType: r.workType || '',
    isAdmin: r.isAdmin,
    isNew: true,
    createdAt: now
  }))

  employees.value.unshift(...newEmps)
  saveToStorage()
  clearUpload()

  if (currentPage.value > totalPages.value && currentPage.value > 1) {
    currentPage.value = totalPages.value
  }

  alert(`成功导入 ${newEmps.length} 名员工！`)
}

function clearUpload() {
  uploadPreview.value = []
  isDragOver.value = false
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      employees.value = JSON.parse(raw)
      return
    }
  } catch (e) {
    console.warn('读取本地存储失败，使用默认数据')
  }
  employees.value = [...DEFAULT_EMPLOYEES]
  saveToStorage()
}

function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(employees.value))
  } catch (e) {
    console.warn('保存到本地存储失败')
  }
}

const orgOptions = computed(() =>
  [...new Set(employees.value.map((e) => e.organization))].sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
)

const filteredEmployees = computed(() => {
  let list = employees.value

  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(
      (e) => e.name.toLowerCase().includes(kw) || e.email.toLowerCase().includes(kw)
    )
  }

  if (filterOrg.value) {
    list = list.filter((e) => e.organization === filterOrg.value)
  }

  if (filterWorkType.value) {
    list = list.filter((e) => e.workType === filterWorkType.value)
  }

  if (filterIsAdmin.value !== '') {
    const admin = filterIsAdmin.value === 'true'
    list = list.filter((e) => Boolean(e.isAdmin) === admin)
  }

  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredEmployees.value.length / pageSize)))
const startIndex = computed(() => (currentPage.value - 1) * pageSize)
const pagedEmployees = computed(() => filteredEmployees.value.slice(startIndex.value, startIndex.value + pageSize))

const formValid = computed(() => {
  return formData.name.trim() && formData.email.trim() && formData.organization.trim()
})

function resetForm() {
  formData.name = ''
  formData.email = ''
  formData.position = ''
  formData.organization = ''
  formData.workType = ''
  formData.isAdmin = false
  formData.isNew = true
}

function openAddDialog() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(emp) {
  isEditing.value = true
  editingId.value = emp.id
  formData.name = emp.name || ''
  formData.email = emp.email || ''
  formData.position = emp.position || ''
  formData.organization = emp.organization || ''
  formData.workType = emp.workType || ''
  formData.isAdmin = Boolean(emp.isAdmin)
  formData.isNew = Boolean(emp.isNew)
  dialogVisible.value = true
}

function handleSubmit() {
  if (!formValid.value) return

  if (isEditing.value && editingId.value) {
    const idx = employees.value.findIndex((e) => e.id === editingId.value)
    if (idx !== -1) {
      employees.value[idx] = {
        ...employees.value[idx],
        name: formData.name.trim(),
        email: formData.email.trim(),
        position: formData.position.trim(),
        organization: formData.organization.trim(),
        workType: formData.workType || '',
        isAdmin: formData.isAdmin,
        isNew: formData.isNew,
        updatedAt: Date.now()
      }
    }
  } else {
    const newEmp = {
      id: `emp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: formData.name.trim(),
      email: formData.email.trim(),
      position: formData.position.trim(),
      organization: formData.organization.trim(),
      workType: formData.workType || '',
      isAdmin: formData.isAdmin,
      isNew: formData.isNew,
      createdAt: Date.now()
    }
    employees.value.unshift(newEmp)
  }

  saveToStorage()
  dialogVisible.value = false

  if (currentPage.value > totalPages.value && currentPage.value > 1) {
    currentPage.value = totalPages.value
  }
}

function confirmDelete(emp) {
  deleteTarget.value = emp
  deleteConfirmVisible.value = true
}

function handleDelete() {
  if (!deleteTarget.value) return
  employees.value = employees.value.filter((e) => e.id !== deleteTarget.value.id)
  saveToStorage()
  deleteConfirmVisible.value = false
  deleteTarget.value = null

  if (!pagedEmployees.value.length && currentPage.value > 1) {
    currentPage.value--
  }
}

onMounted(() => {
  loadFromStorage()
})
</script>

<style scoped>
.employee-crud-page {
  width: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-field {
  flex: 0 1 220px;
}

.result-count {
  margin-left: auto;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.action-cell {
  white-space: nowrap;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-edit {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}

.btn-edit:hover {
  background: #dbeafe;
}

.btn-delete {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
  margin-left: 6px;
}

.btn-delete:hover {
  background: #fee2e2;
}

.empty-row {
  text-align: center;
  color: #9ca3af;
  padding: 32px 0 !important;
  font-size: 14px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding-top: 16px;
  margin-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.btn-page {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  transition: all 0.15s ease;
}

.btn-page:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #6b7280;
  min-width: 60px;
  text-align: center;
}

.employee-form {
  display: grid;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.required {
  color: #dc2626;
  margin-right: 2px;
}

.select-field {
  appearance: auto;
}

.badge-admin {
  background: #fef3c7;
  color: #92400e;
}

.badge-normal {
  background: #f3f4f6;
  color: #4b5563;
}

.delete-confirm-text {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}

.delete-confirm-text strong {
  color: #dc2626;
}

.danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

.danger:hover {
  background: #b91c1c;
}

.upload-area {
  margin-bottom: 18px;
}

.upload-tip {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  margin: 0 0 10px;
}

.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fafbfc;
}

.drop-zone:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}

.drop-zone.drop-active {
  border-color: #059669;
  background: #d1fae5;
  transform: scale(1.01);
}

.hidden-input {
  display: none;
}

.drop-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
}

.drop-zone p {
  margin: 0 0 6px;
  font-size: 13px;
  color: #374151;
}

.drop-hint {
  font-size: 11px;
  color: #9ca3af;
}

.preview-box {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.preview-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 10px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  display: block;
}

.preview-table th,
.preview-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #f3f4f6;
  text-align: left;
  white-space: nowrap;
}

.preview-table th {
  background: #f9fafb;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.row-invalid {
  background: #fef2f2;
}

.row-invalid td {
  color: #dc2626;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>