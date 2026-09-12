<template>
  <div class="layout">
    <aside class="side">
      <div class="brand">🏅 青训档案</div>
      <nav>
        <router-link to="/players" class="nav-item">学员档案</router-link>
        <router-link v-if="auth.isCoach || auth.isAdmin" to="/promotions" class="nav-item">
          季度升组
        </router-link>
      </nav>
      <div class="side-foot">
        <div class="small muted">{{ auth.user?.full_name }}（{{ roleText }}）</div>
        <button class="btn small" style="margin-top:8px" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const roleText = computed(() => ({ coach: '教练', parent: '家长', admin: '管理员' }[auth.user?.role] || ''))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; height: 100%; }
.side {
  width: 200px; background: #16233b; color: #dfe6f2;
  display: flex; flex-direction: column; padding: 18px 14px;
}
.brand { font-size: 17px; font-weight: 700; color: #fff; margin-bottom: 26px; }
.nav-item {
  display: block; padding: 9px 12px; border-radius: 8px; color: #c6d0e2;
  margin-bottom: 4px;
}
.nav-item:hover { background: #223355; color: #fff; }
.nav-item.router-link-active { background: #2a78d6; color: #fff; }
.side-foot { margin-top: auto; }
.side-foot .small { color: #93a1bb; }
.main { flex: 1; overflow-y: auto; padding: 24px 28px; }
</style>
