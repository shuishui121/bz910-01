<template>
  <div>
    <h2 style="margin-top:0">季度升组建议</h2>
    <div class="card filter-bar">
      <label class="field" style="margin:0;width:120px">年份
        <input v-model.number="seasonYear" type="number" min="2023" max="2030" class="input" />
      </label>
      <label class="field" style="margin:0;width:110px">季度
        <select v-model.number="quarter" class="input">
          <option :value="1">第一季度</option>
          <option :value="2">第二季度</option>
          <option :value="3">第三季度</option>
          <option :value="4">第四季度</option>
        </select>
      </label>
      <button class="btn" @click="load">查询</button>
      <button v-if="canManage" class="btn primary" :disabled="generating" @click="generate">
        {{ generating ? '生成中…' : '按季末体测重新生成（前30%推荐）' }}
      </button>
      <span v-if="msg" class="small" :style="{color: err ? 'var(--serious)' : 'var(--good)'}">{{ msg }}</span>
    </div>

    <div class="card" style="margin-top:14px">
      <table class="data-table">
        <thead>
          <tr>
            <th>学员</th><th>训练组</th><th>体测总分</th><th>组内排名</th>
            <th>百分位</th><th>系统建议</th><th>目标组</th><th>状态</th><th v-if="canManage">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in list" :key="s.id">
            <td>{{ s.player_name }}</td>
            <td>{{ s.group_name }}</td>
            <td><b>{{ s.total_score }}</b></td>
            <td>{{ s.rank_in_group }} / {{ s.cohort_size }}</td>
            <td>{{ s.percentile }}%</td>
            <td>
              <span :class="s.recommended ? 'tag green' : 'tag gray'">
                {{ s.recommended ? '推荐升组' : '继续观察' }}
              </span>
            </td>
            <td>{{ s.target_group || '—' }}</td>
            <td>
              <span :class="statusClass(s.status)">{{ statusText(s.status) }}</span>
            </td>
            <td v-if="canManage">
              <button class="btn small" @click="openConfirm(s)">修改确认</button>
            </td>
          </tr>
          <tr v-if="!loading && !list.length">
            <td :colspan="canManage ? 9 : 8" class="muted">
              本季度尚未生成建议（教练点击上方按钮生成）
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 确认弹窗 -->
    <div v-if="target" class="modal-mask" @click.self="target = null">
      <div class="card modal">
        <h3>确认升组结论 — {{ target.player_name }}</h3>
        <p class="small muted">
          系统：{{ target.recommended ? `推荐升入「${target.target_group}」` : '暂不推荐升组' }}
          （{{ target.group_name }} 内 {{ target.rank_in_group }}/{{ target.cohort_size }}）
        </p>
        <label class="field">教练结论
          <select v-model="form.recommended" class="input">
            <option :value="true">同意升组</option>
            <option :value="false">本期不升组</option>
          </select>
        </label>
        <label class="field">目标训练组
          <input v-model="form.target_group" class="input" :placeholder="target.target_group || '如 提高组'" />
        </label>
        <label class="field">教练评语 / 理由
          <textarea v-model="form.coach_note" class="input"
                    placeholder="可补充技术、心理、出勤等综合判断依据"></textarea>
        </label>
        <div class="row" style="justify-content:flex-end">
          <button class="btn" @click="target = null">取消</button>
          <button class="btn primary" @click="confirm">提交确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const canManage = auth.isCoach || auth.isAdmin

const now = new Date()
const seasonYear = ref(now.getFullYear())
const quarter = ref(Math.floor(now.getMonth() / 3) + 1)
const list = ref([])
const loading = ref(false)
const generating = ref(false)
const msg = ref('')
const err = ref(false)
const target = ref(null)
const form = reactive({ recommended: true, target_group: '', coach_note: '' })

onMounted(load)

async function load() {
  loading.value = true
  msg.value = ''
  try {
    list.value = await http.get('/promotions', {
      params: { season_year: seasonYear.value, quarter: quarter.value },
    })
  } catch (e) {
    err.value = true
    msg.value = e.message
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  err.value = false
  try {
    const data = await http.post('/promotions/generate', null, {
      params: { season_year: seasonYear.value, quarter: quarter.value },
    })
    msg.value = `已生成，更新 ${data.upserted} 条（已确认结论不覆盖）`
    await load()
  } catch (e) {
    err.value = true
    msg.value = e.message
  } finally {
    generating.value = false
  }
}

function openConfirm(s) {
  target.value = s
  form.recommended = s.recommended
  form.target_group = s.target_group || ''
  form.coach_note = s.coach_note || ''
}

async function confirm() {
  await http.put(`/promotions/${target.value.id}/confirm`, {
    recommended: form.recommended,
    target_group: form.target_group || null,
    coach_note: form.coach_note,
  }, { params: { season_year: seasonYear.value } })
  target.value = null
  await load()
}

function statusText(s) {
  return { suggested: '待确认', confirmed: '教练已确认', adjusted: '教练已调整', rejected: '已驳回' }[s]
}
function statusClass(s) {
  return {
    suggested: 'tag',
    confirmed: 'tag green',
    adjusted: 'tag',
    rejected: 'tag red',
  }[s]
}
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { border: 1px solid var(--line); padding: 8px 10px; text-align: center; }
.data-table th { background: #f7f6f2; color: var(--ink-2); }
.modal-mask { position: fixed; inset: 0; background: rgba(15,20,30,.45); display: grid; place-items: center; z-index: 50; }
.modal { width: 520px; max-width: 92vw; }
</style>
