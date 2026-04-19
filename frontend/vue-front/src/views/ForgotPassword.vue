<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>找回密码</h2>
      <div class="auth-form-item">
        <input v-model="form.email" placeholder="注册邮箱" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <div class="code-input-wrapper">
          <input v-model="form.code" placeholder="验证码" class="auth-input" />
          <button class="code-button" @click="sendCode" :disabled="countdown > 0 || !form.email">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </button>
        </div>
      </div>
      <div class="auth-form-item">
        <input type="password" v-model="form.new_password" placeholder="新密码" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <input type="password" v-model="form.confirm_password" placeholder="确认密码" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <button class="auth-button" @click="handleReset">重置密码</button>
      </div>
      <div class="auth-link">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = reactive({ email: '', code: '', new_password: '', confirm_password: '' })
const countdown = ref(0)
const router = useRouter()

const sendCode = async () => {
  if (!form.email) return ElMessage.warning('请输入邮箱')
  try {
    await api.post('/user/reset-password', { email: form.email })
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  }
}

const handleReset = async () => {
  if (!form.email || !form.code || !form.new_password || !form.confirm_password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.new_password !== form.confirm_password) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  try {
    await api.post('/user/reset-password', {
      email: form.email,
      code: form.code,
      new_password: form.new_password
    })
    ElMessage.success('密码重置成功，请重新登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  }
}
</script>

<style scoped src="../styles/auth.css"></style>