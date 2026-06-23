export function canAccessRoute(route, user) {
  const allowedRoles = route.meta?.roles

  if (!allowedRoles?.length) return true
  if (!user?.role || !allowedRoles.includes(user.role)) return false

  return true
}
