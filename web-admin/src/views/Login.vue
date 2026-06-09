<template>
  <div class="login-page">
    <div class="login-box">
      <h2>金融业务绩效管理系统</h2>

      <input v-model="username" placeholder="请输入用户ID" />
      <input v-model="password" placeholder="请输入密码" type="password" />
      <p class="login-tip">系统将根据账号自动识别权限级别。</p>

      <button @click="handleLogin">登录</button>
      <button class="forgot-password" type="button" @click="handleForgotPassword">忘记密码</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDefaultPath, setCurrentUser } from '../auth/permissions'
import { login } from '../api/auth'

const username = ref('')
const password = ref('')

const router = useRouter()

function handleLogin() {
  if (username.value && password.value) {
    loginWithCredentials()
  } else {
    alert('请输入用户ID和密码')
  }
}

function handleForgotPassword() {
  router.push('/forgot-password')
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
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 32px;
  box-sizing: border-box;
  background: #f2f4f8;
}

.login-box {
  width: min(100%, 380px);
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

.login-box .forgot-password {
  height: auto;
  margin-top: 14px;
  background: transparent;
  color: #1677ff;
  font-size: 14px;
}

@media (max-width: 980px) {
  .login-page {
    align-items: center;
  }
}
</style>
