<template>
  <div v-if="player">
    <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="margin:0">
        <a href="#/players" class="back">‹</a>
        {{ player.name }}
        <span class="tag gray">{{ player.group_name }}</span>
        <span class="tag" v-if="canWrite">教练视图</span>
        <span class="tag green" v-else>家长只读视图</span>
      </h2>
      <label class="field" style="margin:0;width:130px">赛季年份
        <select v-model.number="seasonYear" class="input" @change="reloadAll">
          <option v-for="y in years" :key="y" :value="y">{{ y }} 赛季</option>
        </select>
      </label>
    </div>

    <div class="tabs">
      <button v-for="t in tabs" :key="t.key"
              :class="['tab', { active: tab === t.key }]"
              @click="tab = t.key">
        {{ t.label }}
      </button>
    </div>

    <div class="card" style="margin-top:14px">
      <!-- 档案概览 -->
      <div v-if="tab === 'overview'" class="overview">
        <p>性别：{{ player.gender === 'male' ? '男' : '女' }}
          出生日期：{{ player.birth_date }}
          {{ player.joined_year }} 年入队
          状态：{{ {active:'在训', promoted:'已升组', left:'离队'}[player.status] }}</p>
        <div v-if="chart?.totals?.length" class="row stats">
          <div class="stat">
            <div class="stat-num">{{ chart.totals[0].total_score ?? '—' }}</div>
            <div class="small muted">首次体测总分</div>
          </div>
          <div class="stat">
            <div class="stat-num">{{ chart.totals.at(-1).total_score ?? '—' }}</div>
            <div class="small muted">最近体测总分</div>
          </div>
          <div class="stat" :class="delta >= 0 ? 'up' : 'down'">
            <div class="stat-num">{{ delta >= 0 ? '+' : '' }}{{ delta.toFixed(1) }}</div>
            <div class="small muted">赛季累计变化(T分)</div>
          </div>
        </div>
      </div>

      <!-- 周训练(家长只读) -->
      <template v-else-if="tab === 'training'">
        <TrainingWeekEditor v-if="canWrite" :key="'tw'+seasonYear"
                            :player-id="playerId" :season-year="seasonYear" />
        <TrainingWeekViewer v-else :key="'tv'+seasonYear"
                            :player-id="playerId" :season-year="seasonYear" />
      </template>

      <!-- 体测 + 成长曲线 -->
      <template v-else-if="tab === 'fitness'">
        <FitnessPanel v-if="canWrite" :key="'fp'+seasonYear"
                      :player-id="playerId" :season-year="seasonYear" />
        <h3>成长曲线（标准分 T，均值 50）</h3>
      </template>

      <!-- 评语 -->
      <CommentPanel v-else-if="tab === 'comments'"
                    :key="'cp'+seasonYear"
                    :player-id="playerId" :season-year="seasonYear"
                    :can-write="canWrite" />
    </div>

    <div v-if="tab === 'fitness'" class="card" style="margin-top:14px">
      <GrowthChart :chart="chart" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'
import GrowthChart from '../components/GrowthChart.vue'
import FitnessPanel from '../components/FitnessPanel.vue'
import CommentPanel from '../components/CommentPanel.vue'
import TrainingWeekEditor from '../components/TrainingWeekEditor.vue'
import TrainingWeekViewer from '../components/TrainingWeekViewer.vue'

const props = defineProps({ id: String })
const playerId = computed(() => props.id)
const auth = useAuthStore()

const player = ref(null)
const tab = ref('overview')
const seasonYear = ref(2026)
const years = [2026, 2025, 2024, 2023]
const chart = ref({ weeks: [], series: [], totals: [] })

const canWrite = computed(() => auth.isCoach || auth.isAdmin)
const tabs = computed(() => {
  const base = [
    { key: 'overview', label: '档案概览' },
    { key: 'training', label: '周训练' },
    { key: 'fitness', label: '体测与成长曲线' },
    { key: 'comments', label: '月度评语' },
  ]
  return base
})
const delta = computed(() => {
  const t = chart.value.totals
  if (!t || t.length < 2) return 0
  return (Number(t.at(-1).total_score) || 0) - (Number(t[0].total_score) || 0)
})

onMounted(async () => {
  player.value = await http.get(`/players/${playerId.value}`)
  await loadChart()
})

async function loadChart() {
  chart.value = await http.get(`/players/${playerId.value}/fitness/growth-chart`, {
    params: { season_year: seasonYear.value },
  })
}
async function reloadAll() {
  await loadChart()
}
watch(tab, async (v) => {
  if (v === 'fitness') await loadChart()
})
</script>

<style scoped>
.back { font-size: 22px; margin-right: 6px; }
.tabs { display: flex; gap: 6px; }
.tab {
  border: 1px solid var(--line); background: #fff; padding: 8px 18px;
  border-radius: 8px 8px 0 0; cursor: pointer; font-size: 13px;
}
.tab.active { background: var(--surface); border-bottom-color: var(--surface); color: var(--brand); font-weight: 600; position: relative; top: 1px; }
.stats { margin-top: 10px; }
.stat {
  background: #f7f9fd; border: 1px solid var(--line); border-radius: 8px;
  padding: 12px 22px; text-align: center;
}
.stat-num { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat.up .stat-num { color: var(--good); }
.stat.down .stat-num { color: var(--serious); }
</style>
