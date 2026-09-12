<template>
  <div>
    <h3 style="margin-top:0">每周训练内容（只读）</h3>
    <div v-if="loading" class="muted">加载中…</div>
    <div v-else-if="!weeks.length" class="muted small">本赛季暂无训练记录</div>
    <div v-for="w in weeks" :key="w.id" class="week-card">
      <div class="week-head">
        <strong>第 {{ w.week_no }} 周</strong>
        <span class="small muted">{{ w.training_date }}</span>
      </div>
      <div class="small muted" v-if="w.technical_items?.length">技术项：
        <span v-for="(t, i) in w.technical_items" :key="i">
          {{ t.name }}{{ t.sets ? ` ${t.sets}组` : '' }}{{ t.reps ? `×${t.reps}` : '' }}；
        </span>
      </div>
      <div class="small muted" v-if="w.physical_items?.length">体能项：
        <span v-for="(t, i) in w.physical_items" :key="i">
          {{ t.name }}{{ t.load ? ` ${t.load}` : '' }}{{ t.sets ? ` ${t.sets}组` : '' }}；
        </span>
      </div>
      <div class="small" v-if="w.matches?.length">对抗赛：
        <span v-for="(m, i) in w.matches" :key="i"
              :style="{color: {胜:'var(--good)', 负:'var(--serious)'}[m.result]}">
          {{ m.name }} {{ m.score }} {{ m.result }}；
        </span>
      </div>
      <p v-if="w.summary" class="summary">小结：{{ w.summary }}</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../api/http.js'

const props = defineProps({
  playerId: [String, Number],
  seasonYear: Number,
})
const weeks = ref([])
const loading = ref(true)

onMounted(async () => {
  weeks.value = await http.get(`/players/${props.playerId}/training-weeks`, {
    params: { season_year: props.seasonYear },
  })
  loading.value = false
})
</script>

<style scoped>
.week-card { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; }
.week-head { display: flex; justify-content: space-between; margin-bottom: 4px; }
.summary { margin: 6px 0 0; color: var(--ink-2); font-size: 13px; }
</style>
