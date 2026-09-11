<template>
  <div class="login-wrap">
    <form class="card login-card" @submit.prevent="submit">
      <h2>省队青训营训练档案平台</h2>
      <p class="muted small">教练 / 家长 请使用分配的账号登录</p>
      <label class="field">用户名
        <input v-model="username" class="input" placeholder="coach_li / parent_ming" autofocus />
      </label>
      <label class="field">密码
        <input v-model="password" type="password" class="input" placeholder="演示: coach123 / parent123" />
      </label>
      <div v-if="error" class="err">{{ error }}</div>
      <button class="btn primary" style="width:100%" :disabled="loading">
        {{ loading ? '登录中…' : '登 录' }}
      </button>
      <p class="muted small" style="margin-top:14px">
        演示账号：coach_li / coach123，coach_wang / coach123，parent_ming / parent123
      </p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    router.push('/players')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100%; display: grid; place-items: center; background: var(--bg); }
.login-card { width: 380px; padding: 30px 32px; }
.login-card h2 { margin: 0 0 6px; font-size: 18px; }
.err { color: var(--serious); font-size: 13px; margin-bottom: 10px; }
</style>
