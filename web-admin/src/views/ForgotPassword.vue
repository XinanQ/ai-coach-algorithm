<template>
  <div class="reset-page">
    <div class="reset-card">
      <button class="back-link" type="button" @click="router.push('/login')">返回登录</button>

      <header class="reset-header">
        <h2>忘记密码</h2>
        <p>请按流程完成身份确认与核验后设置新密码。</p>
      </header>

      <ol class="step-list">
        <li :class="{ active: step === 1, done: step > 1 }">身份确认</li>
        <li :class="{ active: step === 2, done: step > 2 }">身份核验</li>
        <li :class="{ active: step === 3 }">设置新密码</li>
      </ol>

      <form v-if="step === 1" class="reset-form" @submit.prevent="confirmIdentity">
        <label class="field-group">
          账号 / 工号 / 绑定手机号
          <input v-model.trim="identity" placeholder="请输入账号、工号或绑定手机号" />
        </label>

        <label class="field-group">
          图形验证码
          <div class="captcha-row">
            <input v-model.trim="captcha" placeholder="请输入验证码" />
            <button class="captcha-code" type="button" @click="refreshCaptcha">{{ captchaCode }}</button>
          </div>
        </label>

        <label class="field-group">
          安全滑块
          <input v-model.number="sliderValue" type="range" min="0" max="100" />
          <span class="slider-state">{{ sliderValue >= 100 ? '验证通过' : '请拖动滑块到最右侧' }}</span>
        </label>

        <button class="primary-button" type="submit" :disabled="loading">下一步</button>
      </form>

      <form v-else-if="step === 2" class="reset-form" @submit.prevent="verifyCode">
        <div class="verify-target">
          <strong>短信验证码</strong>
          <span>验证码将发送至 {{ maskedMobile || '账号绑定手机' }}。</span>
          <small v-if="emailAvailable">如已绑定邮箱，也可使用邮箱验证码作为备选核验方式。</small>
        </div>

        <label class="field-group">
          验证码
          <div class="captcha-row">
            <input v-model.trim="smsCode" placeholder="请输入短信验证码" />
            <button class="send-code" type="button" :disabled="loading" @click="sendCode">
              {{ codeSent ? '重新发送' : '发送验证码' }}
            </button>
          </div>
        </label>

        <button class="secondary-button" type="button" @click="step = 1">上一步</button>
        <button class="primary-button" type="submit" :disabled="loading">下一步</button>
      </form>

      <form v-else class="reset-form" @submit.prevent="handleSubmitPassword">
        <label class="field-group">
          新密码
          <input v-model="newPassword" placeholder="请输入新密码" type="password" />
        </label>

        <label class="field-group">
          确认新密码
          <input v-model="confirmPassword" placeholder="请再次输入新密码" type="password" />
        </label>

        <button class="secondary-button" type="button" @click="step = 2">上一步</button>
        <button class="primary-button" type="submit" :disabled="loading">提交并返回登录</button>
      </form>

      <p v-if="message" class="reset-message">{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { usePasswordResetFlow } from '../composables/usePasswordResetFlow'

const router = useRouter()
const {
  step,
  identity,
  captcha,
  captchaCode,
  sliderValue,
  smsCode,
  codeSent,
  newPassword,
  confirmPassword,
  maskedMobile,
  emailAvailable,
  loading,
  message,
  refreshCaptcha,
  confirmIdentity,
  sendCode,
  verifyCode,
  submitPassword
} = usePasswordResetFlow()

async function handleSubmitPassword() {
  const submitted = await submitPassword()

  if (submitted) {
    router.push('/login')
  }
}
</script>

<style scoped>
.reset-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 32px;
  box-sizing: border-box;
  background: #f2f4f8;
}

.reset-card {
  width: min(100%, 520px);
  padding: 32px;
  box-sizing: border-box;
  border-radius: 12px;
  background: #fff;
}

.back-link {
  padding: 0;
  border: none;
  background: transparent;
  color: #1677ff;
  cursor: pointer;
}

.reset-header {
  margin-top: 18px;
}

.reset-header h2 {
  margin-bottom: 8px;
  text-align: center;
}

.reset-header p {
  color: #6b7280;
  font-size: 14px;
  text-align: center;
}

.step-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 24px 0;
  padding: 0;
  list-style: none;
}

.step-list li {
  padding: 10px 8px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 14px;
  text-align: center;
}

.step-list li.active,
.step-list li.done {
  background: #e8f2ff;
  color: #1677ff;
}

.reset-form {
  display: grid;
  gap: 16px;
}

.field-group {
  display: grid;
  gap: 8px;
  color: #374151;
  font-size: 14px;
}

.field-group input {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
}

.field-group input[type='range'] {
  padding: 0;
}

.captcha-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px;
  gap: 10px;
}

.captcha-code,
.send-code,
.primary-button,
.secondary-button {
  height: 38px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.captcha-code:disabled,
.send-code:disabled,
.primary-button:disabled,
.secondary-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.captcha-code,
.send-code {
  background: #f3f4f6;
  color: #111827;
}

.primary-button {
  background: #1677ff;
  color: #fff;
}

.secondary-button {
  background: #eef2f7;
  color: #374151;
}

.slider-state,
.reset-message,
.verify-target span,
.verify-target small {
  color: #6b7280;
  font-size: 13px;
}

.verify-target {
  display: grid;
  gap: 4px;
}

.reset-message {
  margin-top: 16px;
}

@media (max-width: 560px) {
  .reset-card {
    padding: 24px;
  }

  .step-list,
  .captcha-row {
    grid-template-columns: 1fr;
  }
}
</style>
