<template>
  <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" style="max-width: 450px; margin: 80px auto">
    <h2>找回密码</h2>

    <el-form-item label="邮箱" prop="email">
      <el-input v-model="form.email" placeholder="请输入注册邮箱">
        <template #append>
          <el-button @click="sendResetCode" :disabled="countdown > 0 || !form.email">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </el-button>
        </template>
      </el-input>
    </el-form-item>

    <el-form-item label="验证码" prop="code">
      <el-input v-model="form.code" placeholder="请输入验证码" />
    </el-form-item>

    <el-form-item label="新密码" prop="new_password">
      <el-input type="password" v-model="form.new_password" placeholder="至少8位，包含字母和数字" />
    </el-form-item>

    <el-form-item label="确认密码" prop="confirm_password">
      <el-input type="password" v-model="form.confirm_password" placeholder="请再次输入新密码" />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="handleReset" :loading="submitting">重置密码</el-button>
      <router-link to="/login">返回登录</router-link>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const formRef = ref(null)
const router = useRouter()
const countdown = ref(0)
const submitting = ref(false)

const form = reactive({
  email: '',
  code: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d)/, message: '密码必须包含字母和数字', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

const sendResetCode = async () => {
  if (!form.email) {
    ElMessage.warning('请输入邮箱')
    return
  }
  try {
    await api.post('/user/reset-password', { email: form.email })
    ElMessage.success('验证码已发送至邮箱，请查收')
    countdown.value = 60
    const timer = setInterval(() => {
      if (countdown.value <= 0) clearInterval(timer)
      else countdown.value--
    }, 1000)
  } catch (err) {
    const msg = err.response?.data?.detail || '发送失败'
    ElMessage.error(msg)
  }
}

const handleReset = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await api.post('/user/reset-password', {
        email: form.email,
        code: form.code,
        new_password: form.new_password
      })
      ElMessage.success('密码重置成功，请重新登录')
      router.push('/login')
    } catch (err) {
      const errData = err.response?.data
      let msg = '重置失败'
      if (errData?.detail) {
        msg = errData.detail
      } else if (errData?.on_field_errors) {
        msg = errData.on_field_errors.join('；')
      } else if (errData?.new_password) {
        msg = errData.new_password[0]
      }
      ElMessage.error(msg)
    } finally {
      submitting.value = false
    }
  })
}
</script>