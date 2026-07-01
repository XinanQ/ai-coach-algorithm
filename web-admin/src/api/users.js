import { request } from './request'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function normalizeEmployee(employee) {
  return {
    id: employee.id,
    name: employee.name,
    email: employee.email,
    position: employee.position,

    age: employee.age,
    department: employee.department,

    organizationId: employee.organizationId,
    organizationName: employee.organizationName,
    organization: employee.organizationName,

    backendLevel: employee.level,
    level: employee.level,

    isNew: employee.isNew,
    workType: employee.workType,
    isAdmin: employee.isAdmin,
    employeeNo: employee.employeeNo,

    isInProject: employee.isInProject,
    joinedProject: employee.isInProject
  }
}

function toEmployeePayload(data) {
  const payload = {
    name: data.name?.trim(),
    email: data.email?.trim(),
    position: data.position?.trim() || null,
    organizationId: data.organizationId != null ? Number(data.organizationId) : null,
    workType: data.workType || null,
    isNew: Boolean(data.isNew),
    isAdmin: Boolean(data.isAdmin),
    isInProject: Boolean(data.isInProject)
  }

  if (data.age != null && data.age !== '') {
    payload.age = Number(data.age)
  }
  if (data.department?.trim()) {
    payload.department = data.department.trim()
  }
  if (data.level?.trim()) {
    payload.level = data.level.trim()
  }

  return payload
}

export async function getUsers() {
  const response = await request('/api/admin/employees')

  const employees = Array.isArray(response)
    ? response
    : response?.data || []

  return employees.map(normalizeEmployee)
}

export async function getEmployee(id) {
  const employee = await request(`/api/admin/employees/${id}`)
  return normalizeEmployee(employee)
}

export async function createEmployee(data) {
  const employee = await request('/api/admin/employees', {
    method: 'POST',
    body: JSON.stringify(toEmployeePayload(data))
  })
  return normalizeEmployee(employee)
}

export async function updateEmployee(id, data) {
  const employee = await request(`/api/admin/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(toEmployeePayload(data))
  })
  return normalizeEmployee(employee)
}

export async function deleteEmployee(id) {
  await request(`/api/admin/employees/${id}`, {
    method: 'DELETE'
  })
}

export async function importEmployeesExcel(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/api/admin/employees/import', {
    method: 'POST',
    body: formData
  })
}

export async function previewEmployeesImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/api/admin/employees/import/preview', {
    method: 'POST',
    body: formData
  })
}

async function downloadExcelFile(path, filename) {
  const token = localStorage.getItem('authToken')
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { 'X-Auth-Token': token } : {}
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `下载失败：${response.status}`)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function downloadEmployeeImportTemplate() {
  await downloadExcelFile('/api/admin/employees/template', 'employee_import_template.xlsx')
}

export async function exportEmployeesExcel() {
  await downloadExcelFile('/api/admin/employees/export', 'employees.xlsx')
}
