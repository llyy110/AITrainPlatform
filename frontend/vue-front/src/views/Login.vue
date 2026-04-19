<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>登录 NeuroStudio</h2>
      <div class="auth-form-item">
        <input
          type="text"
          v-model="form.loginId"
          placeholder="邮箱 / 用户名"
          class="auth-input"
          @keyup.enter="handleLogin"
        />
      </div>
      <div class="auth-form-item">
        <input
          type="password"
          v-model="form.password"
          placeholder="密码"
          class="auth-input"
          @keyup.enter="handleLogin"
        />
      </div>
      <div class="auth-form-item">
        <button class="auth-button" @click="handleLogin">登 录</button>
      </div>
      <div class="auth-link">
        <router-link to="/forgot-password">忘记密码？</router-link>
        <span style="margin:0 10px">|</span>
        <router-link to="/register">去注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const form = reactive({ loginId: '', password: '' })
const userStore = useUserStore()
const router = useRouter()

const handleLogin = async () => {
  if (!form.loginId || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  try {
    await userStore.login(form.loginId, form.password)
    ElMessage.success('登录成功')
    const redirect = sessionStorage.getItem('redirectAfterLogin') || '/dashboard'
    sessionStorage.removeItem('redirectAfterLogin')
    router.push(redirect)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  }
}
</script>

<style scoped src="../styles/auth.css"></style>