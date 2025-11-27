<template>
  <div class="welcome-container">
    <el-card class="welcome-card">
      <h1 class="welcome-title">Welcome</h1>
      <p class="welcome-message">
        You have successfully logged into the system and can now start using various functions.
      </p>
      <el-button type="primary" class="logout-btn" @click="logout">Logout</el-button>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const logout = async () => {
  if (!(await userStore.logout())) {
    router.push('/login')
  }
}
</script>

<style lang="less" scoped>
.welcome-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;

  .welcome-card {
    width: 500px;
    padding: 30px;
    text-align: center;

    .welcome-title {
      color: #409eff;
      margin-bottom: 20px;
    }

    .welcome-message {
      margin-bottom: 30px;
      font-size: 16px;
    }

    .logout-btn {
      width: 200px;
    }
  }
}
</style>
