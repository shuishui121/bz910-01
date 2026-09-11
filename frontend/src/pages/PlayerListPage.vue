<template>
  <div>
    <h2 style="margin-top:0">{{ title }}</h2>
    <div v-if="loading" class="muted">加载中…</div>
    <div v-else-if="!players.length" class="card muted">暂无可查看的学员</div>
    <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(240px,1fr))">
      <div v-for="p in players" :key="p.id" class="card player-card" @click="open(p.id)">
        <div class="avatar">{{ p.name.slice(0, 1) }}</div>
        <div>
          <div class="pname">{{ p.name }}
            <span class="tag gray">{{ p.group_name }}</span>
          </div>
          <div class="small muted">
            {{ p.gender === 'male' ? '男' : '女' }} ·
            {{ ageText(p.birth_date) }}岁 ·
            {{ p.joined_year }} 入队
          </div>
          <div v-if="p.is_lead !== null && p.is_lead !== undefined" class="small" style="margin-top:4px">
            <span :class="p.is_lead ? 'tag green' : 'tag'">{{ p.is_lead ? '主教练' : '协作教练' }}</span>
          </div>
          <div v-if="p.relationship" class="small" style="margin-top:4px">
            <span class="tag">家长账号</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const players = ref([])
const loading = ref(true)

const title = computed(
  auth.isParent ? '我的孩子' : auth.isAdmin ? '全部学员' : '我负责的学员',
)

onMounted(async () => {
  players.value = await http.get('/players')
  loading.value = false
})

function ageText(birth) {
  const b = new Date(birth)
  let age = new Date().getFullYear() - b.getFullYear()
  return age
}
function open(id) {
  router.push(`/players/${id}`)
}
</script>

<style scoped>
.player-card { display: flex; gap: 14px; cursor: pointer; transition: .15s; }
.player-card:hover { border-color: var(--brand); transform: translateY(-2px); }
.avatar {
  width: 44px; height: 44px; border-radius: 50%; background: #2a78d6;
  color: #fff; display: grid; place-items: center; font-size: 18px; flex: none;
}
.pname { font-weight: 600; display: flex; gap: 8px; align-items: center; }
</style>
