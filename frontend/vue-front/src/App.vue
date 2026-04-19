<template>
  <div id="app">
    <el-container>
<!--      <el-header v-if="isLoggedIn">-->
<!--        <el-menu mode="horizontal" router>-->
<!--          <el-menu-item index="/dashboard">控制面板</el-menu-item>-->
<!--          <el-menu-item index="/training/new">我的训练</el-menu-item>-->
<!--          <el-menu-item index="/training/history">训练记录</el-menu-item>-->
<!--          <el-menu-item index="/forum">交流论坛</el-menu-item>-->
<!--          <el-menu-item index="/profile">个人中心</el-menu-item>-->
<!--          <el-menu-item @click="logout" style="float:right">退出</el-menu-item>-->
<!--        </el-menu>-->
<!--      </el-header>-->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
    <!-- 全局智能体悬浮窗 -->
    <AgentChat />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/user'
import AgentChat from './components/AgentChat.vue'

const userStore = useUserStore()
const router = useRouter()
const isLoggedIn = computed(() => userStore.isLoggedIn)

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.el-header {
  background-color: #fff;
  border-bottom: 1px solid #eaeef2;
  padding: 0;
}
</style>