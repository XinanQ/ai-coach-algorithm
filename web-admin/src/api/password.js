import { mockResolve, request } from './request'

const useMockPasswordReset = import.meta.env.VITE_USE_MOCK_PASSWORD_RESET !== 'false'
const mockCaptchas = new Map()

function createMockCode() {
  return Math.random().toString(36).slice(2, 6).toUpperCase()
}

function createMockToken(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export async function getPasswordResetCaptcha() {
  if (!useMockPasswordReset) {
    return request('/api/auth/password-reset/captcha')
  }

  const captchaId = createMockToken('captcha')
  const captchaCode = createMockCode()
  mockCaptchas.set(captchaId, captchaCode)

  return mockResolve({
    captchaId,
    captchaCode
  })
}

export async function confirmPasswordResetIdentity(payload) {
  if (!useMockPasswordReset) {
    return request('/api/auth/password-reset/identity', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  const expectedCode = mockCaptchas.get(payload.captchaId)

  if (!payload.identity) {
    throw new Error('请输入账号、工号或绑定手机号')
  }

  if (!expectedCode || payload.captchaCode?.toUpperCase() !== expectedCode) {
    throw new Error('图形验证码不正确')
  }

  if (!payload.sliderPassed) {
    throw new Error('请完成安全滑块验证')
  }

  return mockResolve({
    resetToken: createMockToken('reset'),
    maskedMobile: '138****5678',
    emailAvailable: true
  })
}

export async function sendPasswordResetCode(payload) {
  if (!useMockPasswordReset) {
    return request('/api/auth/password-reset/code', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  if (!payload.resetToken) {
    throw new Error('身份确认已失效，请重新确认')
  }

  return mockResolve({
    codeToken: createMockToken('code'),
    expiresIn: 300
  })
}

export async function verifyPasswordResetCode(payload) {
  if (!useMockPasswordReset) {
    return request('/api/auth/password-reset/verify', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  if (!payload.resetToken || !payload.codeToken) {
    throw new Error('验证码已失效，请重新发送')
  }

  if (!payload.code) {
    throw new Error('请输入短信验证码')
  }

  return mockResolve({
    verifyToken: createMockToken('verify')
  })
}

export async function resetPassword(payload) {
  if (!useMockPasswordReset) {
    return request('/api/auth/password-reset/password', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  if (!payload.verifyToken) {
    throw new Error('身份核验已失效，请重新核验')
  }

  if (!payload.newPassword || !payload.confirmPassword) {
    throw new Error('请输入并确认新密码')
  }

  if (payload.newPassword !== payload.confirmPassword) {
    throw new Error('两次输入的新密码不一致')
  }

  return mockResolve({
    success: true
  })
}
