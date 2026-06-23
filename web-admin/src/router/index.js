import { createRouter, createWebHistory } from 'vue-router'

import Login from '../views/Login.vue'
import ForgotPassword from '../views/ForgotPassword.vue'
import Dashboard from '../views/Dashboard.vue'
import Organization from '../views/Organization.vue'
import Users from '../views/Users.vue'
import EmployeeCRUD from '../views/EmployeeCRUD.vue'
import Projects from '../views/Projects.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import Indicators from '../views/Indicators.vue'
import Decompose from '../views/Decompose.vue'
import Report from '../views/Report.vue'
import Rankings from '../views/Rankings.vue'
import Forbidden from '../views/Forbidden.vue'
import { canAccessRoute, getCurrentUser, getDefaultPath, isLoggedIn } from '../auth/permissions'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    component: Login,
    meta: {
      public: true
    }
  },
  {
    path: '/forgot-password',
    component: ForgotPassword,
    meta: {
      public: true
    }
  },
  {
    path: '/403',
    component: Forbidden
  },
  {
    path: '/dashboard',
    component: Dashboard,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
    }
  },
  {
    path: '/performance',
    redirect: '/rankings'
  },
  {
    path: '/organization',
    component: Organization,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
    }
  },
  {
    path: '/users',
    component: Users,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
    }
  },
  {
    path: '/projects',
    component: Projects,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin']
    }
  },
  {
    path: '/projects/:id',
    component: ProjectDetail,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin'],
      projectAccess: 'visible'
    }
  },
  {
    path: '/projects/:id/indicators',
    component: Indicators,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin'],
      projectAccess: 'visible'
    }
  },
  {
    path: '/projects/:id/decompose',
    component: Decompose,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin'],
      projectAccess: 'decompose'
    }
  },
  {
    path: '/decomposition',
    component: Decompose,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
    }
  },
  {
    path: '/report',
    component: Report,
    meta: {
      roles: ['outlet_admin', 'employee']
    }
  },
  {
    path: '/rankings',
    component: Rankings,
    meta: {
      roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
    }
  },
  {
    path: '/users/employee-manage',
    component: EmployeeCRUD,
    meta: {
      roles: ['city_admin', 'branch_admin', 'outlet_admin']
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const isPublicRoute = Boolean(to.meta?.public)
  const hasSession = isLoggedIn()
  const currentUser = getCurrentUser()

  if (!isPublicRoute && !hasSession) {
    return '/login'
  }

  if (isPublicRoute && hasSession) {
    return getDefaultPath(currentUser)
  }

  if (!isPublicRoute && to.path !== '/403' && !canAccessRoute(to, currentUser)) {
    return '/403'
  }
})

export default router