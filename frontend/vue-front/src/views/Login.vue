<template>
  <el-form :model="form" label-width="80px" style="max-width: 400px; margin: 100px auto">
    <h2>登录</h2>
    <el-form-item label="账号">
      <el-input v-model="form.loginId" placeholder="邮箱/用户名"/>
    </el-form-item>
    <el-form-item label="密码">
      <el-input type="password" v-model="form.password"/>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleLogin">登录</el-button>
      <router-link to="/forgot-password" style="margin-left: 20px">忘记密码？</router-link>

      <router-link to="/register">去注册</router-link>
    </el-form-item>
  </el-form>
</template>

<script setup>
import {reactive} from 'vue'
import {useRouter} from 'vue-router'
import {useUserStore} from '../stores/user'
import {ElMessage} from 'element-plus'

const form = reactive({loginId: '', password: ''})
const userStore = useUserStore()
const router = useRouter()

const handleLogin = async () => {
  try {
    await userStore.login(form.loginId, form.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  }
}
</script>