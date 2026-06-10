import { ref } from 'vue'
import {
  confirmPasswordResetIdentity,
  getPasswordResetCaptcha,
  resetPassword,
  sendPasswordResetCode,
  verifyPasswordResetCode
} from '../api/password'

export function usePasswordResetFlow() {
  const step = ref(1)
  const identity = ref('')
  const captchaId = ref('')
  const captcha = ref('')
  const captchaCode = ref('')
  const sliderValue = ref(0)
  const smsCode = ref('')
  const codeSent = ref(false)
  const newPassword = ref('')
  const confirmPassword = ref('')
  const resetToken = ref('')
  const codeToken = ref('')
  const verifyToken = ref('')
  const maskedMobile = ref('')
  const emailAvailable = ref(false)
  const loading = ref(false)
  const message = ref('')

  async function runAction(action) {
    loading.value = true

    try {
      await action()
    } catch (error) {
      message.value = error.message
    } finally {
      loading.value = false
    }
  }

  async function refreshCaptcha() {
    try {
      const result = await getPasswordResetCaptcha()
      captchaId.value = result.captchaId
      captchaCode.value = result.captchaCode
      captcha.value = ''
    } catch (error) {
      message.value = error.message
    }
  }

  async function confirmIdentity() {
    await runAction(async () => {
      const result = await confirmPasswordResetIdentity({
        identity: identity.value,
        captchaId: captchaId.value,
        captchaCode: captcha.value,
        sliderPassed: sliderValue.value >= 100
      })

      resetToken.value = result.resetToken
      maskedMobile.value = result.maskedMobile
      emailAvailable.value = result.emailAvailable
      message.value = ''
      step.value = 2
    })
  }

  async function sendCode() {
    await runAction(async () => {
      const result = await sendPasswordResetCode({
        resetToken: resetToken.value,
        channel: 'sms'
      })

      codeToken.value = result.codeToken
      codeSent.value = true
      message.value = `验证码已发送，有效期 ${Math.floor(result.expiresIn / 60)} 分钟`
    })
  }

  async function verifyCode() {
    await runAction(async () => {
      const result = await verifyPasswordResetCode({
        resetToken: resetToken.value,
        codeToken: codeToken.value,
        channel: 'sms',
        code: smsCode.value
      })

      verifyToken.value = result.verifyToken
      message.value = ''
      step.value = 3
    })
  }

  async function submitPassword() {
    let submitted = false

    await runAction(async () => {
      await resetPassword({
        verifyToken: verifyToken.value,
        newPassword: newPassword.value,
        confirmPassword: confirmPassword.value
      })

      submitted = true
    })

    return submitted
  }

  refreshCaptcha()

  return {
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
  }
}
