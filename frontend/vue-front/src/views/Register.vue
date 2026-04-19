<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>注册账号</h2>
      <div class="auth-form-item">
        <input v-model="form.username" placeholder="用户名" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <div class="code-input-wrapper">
          <input v-model="form.email" placeholder="邮箱" class="auth-input" />
          <button class="code-button" @click="sendCode" :disabled="countdown > 0">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </button>
        </div>
      </div>
      <div class="auth-form-item">
        <input v-model="form.code" placeholder="验证码" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <input type="password" v-model="form.password" placeholder="密码" class="auth-input" />
      </div>
      <div class="auth-form-item">
        <button class="auth-button" @click="handleRegister">注 册</button>
      </div>
      <div class="auth-link">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = reactive({ username: '', email: '', code: '', password: '' })
const countdown = ref(0)
const userStore = useUserStore()
const router = useRouter()

const sendCode = async () => {
  if (!form.email) return ElMessage.warning('请输入邮箱')
  try {
    await api.post('/user/send-code', { email: form.email })
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

const handleRegister = async () => {
  if (!form.username || !form.email || !form.code || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await userStore.register(form.username, form.email, form.password, form.code)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  }
}
</script>

<style scoped src="../styles/auth.css"></style>