<template>
  <div>
    <h3>体测录入</h3>
    <div class="row" style="align-items:flex-end">
      <label class="field" style="width:170px">测试日期
        <input v-model="form.test_date" type="date" class="input" />
      </label>
      <label class="field" style="width:120px">对应周次
        <input v-model.number="form.week_no" type="number" min="1" max="53" class="input" />
      </label>
    </div>

    <div class="grid metric-grid">
      <label v-for="m in catalog" :key="m.code" class="field metric-box">
        {{ m.name }}（{{ m.unit }}，{{ m.direction === 'higher_better' ? '越大越好' : '越小越好' }}）
        <input v-model.number="form.metrics[m.code]" type="number" step="0.1" class="input"
               placeholder="未测留空" />
      </label>
    </div>

    <div class="row" style="align-items:center">
      <button class="btn primary" :disabled="saving" @click="save">
        {{ saving ? '提交中…' : '录入住测并计算标准分' }}
      </button>
      <span v-if="msg" class="small" :style="{color: errMsg ? 'var(--serious)' : 'var(--good)'}">{{ msg }}</span>
    </div>

    <h3 style="margin-top:22px">历次体测</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>日期</th><th>周次</th><th>体测总分(T)</th><th>项数</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tests" :key="t.id">
          <td>{{ t.test_date }}</td>
          <td>W{{ t.week_no ?? '—' }}</td>
          <td><b>{{ t.total_score ?? '—' }}</b></td>
          <td>{{ Object.keys(t.metrics).length }}</td>
        </tr>
        <tr v-if="!tests.length"><td colspan="4" class="muted">暂无体测记录</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api/http.js'

const props = defineProps({
  playerId: [String, Number],
  seasonYear: { type: Number, default: 2026 },
})

const catalog = ref([])
const tests = ref([])
const saving = ref(false)
const msg = ref('')
const errMsg = ref(false)

const form = reactive({
  test_date: new Date().toISOString().slice(0, 10),
  week_no: null,
  metrics: {},
})

onMounted(async () => {
  catalog.value = await http.get('/metrics')
  await load()
})

async function load() {
  tests.value = await http.get(`/players/${props.playerId}/fitness`, {
    params: { season_year: props.seasonYear },
  })
}

async function save() {
  const metrics = Object.fromEntries(
    Object.entries(form.metrics).filter(([, v]) => v !== null && v !== '' && !Number.isNaN(v)),
  )
  if (!Object.keys(metrics).length) {
    errMsg.value = true
    msg.value = '请至少填写一项指标'
    return
  }
  saving.value = true
  errMsg.value = false
  try {
    await http.post(`/players/${props.playerId}/fitness`,
      { test_date: form.test_date, week_no: form.week_no, metrics },
      { params: { season_year: props.seasonYear } })
    msg.value = '体测已录入'
    form.metrics = {}
    await load()
  } catch (e) {
    errMsg.value = true
    msg.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.metric-grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px 14px; }
.metric-box { font-size: 12px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
.data-table th, .data-table td { border: 1px solid var(--line); padding: 6px 10px; text-align: center; }
.data-table th { background: #f7f6f2; color: var(--ink-2); }
</style>
