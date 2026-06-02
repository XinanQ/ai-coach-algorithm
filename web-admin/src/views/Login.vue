<template>
  <div class="login-page">
    <div class="login-box">
      <h2>金融业务绩效管理系统</h2>

      <input v-model="username" placeholder="请输入用户名" />
      <input v-model="password" placeholder="请输入密码" type="password" />
      <p class="login-tip">系统将根据账号自动识别权限级别。</p>

      <button @click="handleLogin">登录</button>
      <button class="demo-button" @click="handleDemoLogin">演示登录</button>
    </div>

    <section class="demo-panel">
      <div class="demo-heading">
        <h3>演示账号</h3>
        <span>密码均为 123456</span>
      </div>
      <div class="demo-list">
        <button
          v-for="account in visibleDemoUsers"
          :key="account.username"
          class="account-row"
          @click="fillAccount(account)"
        >
          <strong>{{ account.username }}</strong>
          <span>{{ account.roleName }}</span>
          <span>{{ account.organization }}</span>
          <small>{{ account.dataScope }}</small>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { demoUsers, getDefaultPath, setCurrentUser } from '../auth/permissions'
import { login } from '../api/auth'

const username = ref('')
const password = ref('')

const router = useRouter()

const visibleDemoUsers = computed(() =>
  demoUsers.filter((user) =>
    ['head', 'js_province', 'js_city', 'admin', 'outlet', 'js_employee', 'zj_province', 'zj_city', 'gd_province', 'gd_city', 'gd_employee'].includes(user.username)
  )
)

function handleLogin() {
  if (username.value && password.value) {
    loginWithCredentials()
  } else {
    alert('请输入用户名和密码')
  }
}

function handleDemoLogin() {
  username.value = 'js_province'
  password.value = '123456'
  loginWithCredentials()
}

function fillAccount(account) {
  username.value = account.username
  password.value = account.password
}

async function loginWithCredentials() {
  try {
    const matchedUser = await login(username.value, password.value)
    setCurrentUser(matchedUser)
    router.push(getDefaultPath(matchedUser))
  } catch (error) {
    alert(error.message)
    return
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 380px minmax(420px, 720px);
  gap: 24px;
  justify-content: center;
  align-items: center;
  padding: 32px;
  box-sizing: border-box;
  background: #f2f4f8;
}

.login-box {
  padding: 32px;
  background: white;
  border-radius: 12px;
}

.login-box h2 {
  text-align: center;
  margin-bottom: 24px;
}

.login-box input {
  width: 100%;
  height: 36px;
  margin-bottom: 16px;
  padding: 0 10px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
}

.login-tip {
  margin: -6px 0 16px;
  color: #6b7280;
  font-size: 14px;
}

.login-box button {
  width: 100%;
  height: 38px;
  background: #1677ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.login-box .demo-button {
  margin-top: 10px;
  background: #0f766e;
}

.demo-panel {
  max-height: calc(100vh - 64px);
  overflow: auto;
  padding: 24px;
  border-radius: 12px;
  background: #fff;
}

.demo-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: baseline;
  margin-bottom: 16px;
}

.demo-heading h3 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.demo-heading span,
.account-row small {
  color: #6b7280;
  font-size: 13px;
}

.demo-list {
  display: grid;
  gap: 10px;
}

.account-row {
  width: 100%;
  display: grid;
  grid-template-columns: 130px 110px 150px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.account-row:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}

.account-row strong {
  color: #0f766e;
}

@media (max-width: 980px) {
  .login-page {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .demo-panel {
    max-height: none;
  }

  .account-row {
    grid-template-columns: 1fr;
  }
}
</style>
