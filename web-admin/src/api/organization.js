import { request } from './request'

const BASE_URL = '/api/admin/organizations'

export function getOrganizations() {
  return request(BASE_URL)
}

export function getOrganizationTree() {
  return request(`${BASE_URL}/tree`)
}

export function getOrganizationById(id) {
  return request(`${BASE_URL}/${id}`)
}

export function createOrganization(data, parentId) {
  const query = parentId ? `?parentId=${parentId}` : ''

  return request(`${BASE_URL}${query}`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function updateOrganization(id, data, parentId) {
  const query = parentId ? `?parentId=${parentId}` : ''

  return request(`${BASE_URL}/${id}${query}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export function deleteOrganization(id) {
  return request(`${BASE_URL}/${id}`, {
    method: 'DELETE'
  })
}

export function getOrganizationsByLevel(level) {
  return request(`${BASE_URL}/by-level/${level}`)
}