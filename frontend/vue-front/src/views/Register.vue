<template>
  <el-form :model="form" label-width="100px" style="max-width: 450px; margin: 80px auto">
    <h2>注册</h2>
    <el-form-item label="用户名">
      <el-input v-model="form.username"/>
    </el-form-item>
    <el-form-item label="邮箱">
      <el-input v-model="form.email">
        <template #append>
          <el-button @click="sendCode" :disabled="countdown > 0">{{
              countdown > 0 ? `${countdown}s` : '获取验证码'
            }}
          </el-button>
        </template>
      </el-input>
    </el-form-item>
    <el-form-item label="验证码">
      <el-input v-model="form.code"/>
    </el-form-item>
    <el-form-item label="密码">
      <el-input type="password" v-model="form.password"/>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleRegister">注册</el-button>
      <router-link to="/login">已有账号？去登录</router-link>
    </el-form-item>
  </el-form>
</template>

<script setup>
import {reactive, ref} from 'vue'
import {useRouter} from 'vue-router'
import {useUserStore} from '../stores/user'
import {ElMessage} from 'element-plus'
import api from '../api'

const form = reactive({username: '', email: '', code: '', password: ''})
const countdown = ref(0)
const userStore = useUserStore()
const router = useRouter()

const sendCode = async () => {
  if (!form.email) return ElMessage.warning('请输入邮箱')
  try {
    // 获取CSRF Token
    const csrfToken = getCookie('csrftoken');

    await api.post('/user/send-code', {email: form.email}, {
      headers: {
        'X-CSRFToken': csrfToken,  // 关键：添加CSRF Token
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      if (countdown.value <= 0) clearInterval(timer)
      else countdown.value--
    }, 1000)
  } catch (e) {
    console.log(e)
    ElMessage.error(e.response?.data?.detail || '发送失败')
  }
}

// 辅助函数：从cookie获取值
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}

const handleRegister = async () => {
  try {
    await userStore.register(form.username, form.email, form.password, form.code)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    const errData = e.response?.data
    let msg = '注册失败'
    if (errData?.detail) {
      msg = errData.detail
    } else if (errData?.on_field_errors) {
      msg = errData.on_field_errors.join('；')
    } else if (typeof errData === 'object') {
      const allErrors = Object.values(errData).flat()
      if (allErrors.length) msg = allErrors.join('；')
    }
    ElMessage.error(msg)
  }
}
</script>