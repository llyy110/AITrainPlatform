<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '80px' : '260px'" class="sidebar">
      <div class="logo-area">
        <el-icon :size="32" color="#409eff">
          <Cpu/>
        </el-icon>
        <span v-show="!isCollapse" class="logo-text">Neuro<span>Studio</span></span>
      </div>
      <el-menu
          :default-active="$route.path"
          router
          :collapse="isCollapse"
          :collapse-transition="false"
          background-color="transparent"
          text-color="#ffffffb3"
          active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon>
            <DataBoard/>
          </el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/training/new">
          <el-icon>
            <Cpu/>
          </el-icon>
          <span>我的训练</span>
        </el-menu-item>
        <el-menu-item index="/training/history">
          <el-icon>
            <List/>
          </el-icon>
          <span>训练历史</span>
        </el-menu-item>
        <el-menu-item index="/forum">
          <el-icon>
            <ChatLineSquare/>
          </el-icon>
          <span>社区</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isLoggedIn" index="/profile">
          <el-icon>
            <User/>
          </el-icon>
          <span>个人中心</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-button :icon="isCollapse ? Expand : Fold" @click="isCollapse = !isCollapse" text/>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-switch
              v-model="isDark"
              :active-icon="Moon"
              :inactive-icon="Sunny"
              inline-prompt
              @change="toggleDark"
          />
          <MessageCenter v-if="userStore.isLoggedIn"/>          <!-- 登录状态显示用户信息，未登录显示登录/注册按钮 -->
          <el-dropdown v-if="userStore.isLoggedIn" @command="handleUserCommand">
            <span class="user-info">
              <el-avatar :size="36" :src="userStore.userInfo.avatar"/>
              <span class="username">{{ userStore.userInfo.username || '用户' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div v-else class="auth-buttons">
            <el-button link @click="$router.push('/login')">登录</el-button>
            <el-button type="primary" size="small" @click="$router.push('/register')">注册</el-button>
          </div>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component"/>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
  <!-- 全局悬浮助手 -->
  <AgentChat/>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {useDark, useToggle} from '@vueuse/core'
import {useUserStore} from '@/stores/user'
import {useTrainingStore} from '@/stores/training'
import {useRouter} from 'vue-router'
import {ChatLineSquare, Cpu, DataBoard, Expand, Fold, List, Moon, Sunny, User} from '@element-plus/icons-vue'
import AgentChat from '@/components/AgentChat.vue'
import MessageCenter from '@/components/MessageCenter.vue'
import {ElMessage} from 'element-plus'

const isCollapse = ref(false)
const isDark = useDark()
const toggleDark = useToggle(isDark)
const userStore = useUserStore()
const trainingStore = useTrainingStore()
const router = useRouter()

const restoreLatestTraining = async () => {
  if (!userStore.isLoggedIn) return
  if (trainingStore.currentTaskId && !trainingStore.isTaskExpired()) {
    if (router.currentRoute.value.path !== '/training/new') {
      router.push('/training/new')
    }
    return
  }
  const latest = await trainingStore.getLatestTraining()
  if (latest && (latest.status === 'training' || latest.status === 'pending')) {
    const createdAt = new Date(latest.created_at).getTime()
    const elapsed = Date.now() - createdAt
    if (elapsed <= 10 * 60 * 1000) {
      trainingStore.setCurrentTaskId(latest.task_id)
      ElMessage.info(`恢复未完成的训练任务：${latest.model_type}`)
      if (router.currentRoute.value.path !== '/training/new') {
        router.push('/training/new')
      }
    }
  }
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    restoreLatestTraining()
  }
})

const handleUserCommand = (cmd) => {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(165deg, #13203a 0%, #0b1426 100%);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow-x: hidden;

  .logo-area {
    padding: 20px 16px;
    display: flex;
    align-items: center;
    gap: 10px;

    .el-icon {
      flex-shrink: 0;
    }

    .logo-text {
      font-size: 20px;
      font-weight: 700;
      color: white;

      span {
        color: #409eff;
      }
    }
  }

  .el-menu {
    border-right: none;
    flex: 1;

    .el-menu-item {
      border-radius: 12px;
      margin: 4px 8px;

      &.is-active {
        background: rgba(64, 158, 255, 0.2) !important;
      }

      &:hover {
        background: rgba(255, 255, 255, 0.1) !important;
      }
    }
  }

  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;

    .el-button {
      color: #bbb;
    }
  }
}

.app-header {
  background: var(--card-bg);
  backdrop-filter: blur(8px);
  border-bottom: var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;

    .username {
      font-weight: 500;
    }
  }

  .notice-badge {
    margin-right: 8px;
  }

  .auth-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.app-main {
  height: calc(100vh - 64px); // 64px 为头部 .el-header 的高度
  padding: 24px;
  background: transparent;
  overflow-y: auto;
}

.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.25s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>