import { request } from './request'

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

    isInProject: employee.isInProject,
    joinedProject: employee.isInProject
  }
}

export async function getUsers() {
  const response = await request('/api/admin/employees')

  const employees = Array.isArray(response)
      ? response
      : response?.data || []

  return employees.map(normalizeEmployee)
}