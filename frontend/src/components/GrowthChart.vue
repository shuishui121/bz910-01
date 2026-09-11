<template>
  <div class="viz-root">
    <div class="toolbar">
      <div class="legend">
        <button
          v-for="(s, i) in chart.series"
          :key="s.code"
          class="legend-item"
          :class="{ off: !visible.has(s.code) }"
          @click="toggle(s.code)"
        >
          <span class="swatch" :style="{ background: color(i) }"></span>{{ s.name }}
        </button>
      </div>
      <button class="btn small" @click="showTable = !showTable">
        {{ showTable ? '图形视图' : '表格视图' }}
      </button>
    </div>

    <div v-if="!chart.series.length" class="muted" style="padding:30px 0;text-align:center">
      该赛季暂无体测数据,无法生成成长曲线
    </div>

    <div v-else-if="!showTable" class="plot-area" @mouseleave="hoverIdx = null"
         @mousemove="onMove">
      <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="plot-svg">
        <!-- 网格与纵轴刻度(标准分) -->
        <g v-for="g in gridYs" :key="g.v">
          <line :x1="pad.l" :x2="W - pad.r" :y1="g.y" :y2="g.y" class="grid" />
          <text :x="pad.l - 8" :y="g.y + 4" text-anchor="end" class="tick">{{ g.v }}</text>
        </g>
        <line :x1="pad.l" :x2="W - pad.r" :y1="y(50)" :y2="y(50)" class="baseline" />

        <!-- 横轴周数 -->
        <text v-for="(wk, i) in chart.weeks" :key="wk"
              :x="x(i)" :y="H - pad.b + 20" text-anchor="middle" class="tick">
          W{{ wk }}
        </text>
        <text :x="12" :y="16" class="axis-title">标准分 T(均值=50)</text>
        <text :x="W - pad.r" :y="H - 4" text-anchor="end" class="axis-title">训练周数</text>

        <!-- 十字线 -->
        <line v-if="hoverIdx !== null" :x1="x(hoverIdx)" :x2="x(hoverIdx)"
              :y1="pad.t" :y2="H - pad.b" class="crosshair" />

        <!-- 各指标折线 -->
        <g v-for="(s, si) in chart.series" :key="s.code" v-show="visible.has(s.code)">
          <polyline :points="pointsOf(s)" fill="none" :stroke="color(si)"
                    stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          <circle v-for="(pt, pi) in byWeek(s)" :key="pi"
                  :cx="x(pi)" :cy="pt ? y(pt.score) : 0" r="4.5"
                  :fill="color(si)" :opacity="pt ? 1 : 0"
                  stroke="var(--surface)" stroke-width="2" />
        </g>
      </svg>

      <!-- tooltip -->
      <div v-if="hoverIdx !== null" class="tip" :style="tipStyle">
        <div class="tip-head">第 {{ chart.weeks[hoverIdx] }} 周</div>
        <div v-for="(s, si) in chart.series.filter(x => visible.has(x.code))"
             :key="s.code" class="tip-row">
          <span class="swatch" :style="{ background: color(si) }"></span>
          <span class="tip-name">{{ s.name }}</span>
          <span class="tip-val">{{ fmt(s.data[hoverIdx]) }}</span>
        </div>
      </div>
    </div>

    <!-- 表格视图(色盲/打印友好) -->
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>周次</th>
          <th v-for="s in visibleSeries" :key="s.code">
            {{ s.name }} 原始值/标准分
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(wk, i) in chart.weeks" :key="wk">
          <td>第 {{ wk }} 周</td>
          <td v-for="s in visibleSeries" :key="s.code">
            <template v-if="s.data[i]">{{ s.data[i].raw }} {{ s.unit }} / {{ s.data[i].score }}</template>
            <span v-else class="muted">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { seriesColor } from '../styles.colors.js'

const props = defineProps({ chart: { type: Object, required: true } })

const W = 760
const H = 340
const pad = { l: 46, r: 18, t: 26, b: 40 }
const Y_MIN = 20
const Y_MAX = 80

const visible = reactive(new Set())
const showTable = ref(false)
const hoverIdx = ref(null)

const color = (i) => seriesColor(i)

// 后端 series.data 按各自测试次数排列;用 weeks 对齐成等长数组
function byWeek(s) {
  const map = new Map(s.data.map((d) => [d.week, d]))
  return props.chart.weeks.map((w) => map.get(w) || null)
}

function x(i) {
  const n = props.chart.weeks.length
  if (n <= 1) return pad.l + (W - pad.l - pad.r) / 2
  return pad.l + (i * (W - pad.l - pad.r)) / (n - 1)
}
function y(v) {
  return H - pad.b - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * (H - pad.t - pad.b)
}

const gridYs = computed(() =>
  [20, 35, 50, 65, 80].map((v) => ({ v, y: y(v) })),
)

const visibleSeries = computed(() =>
  props.chart.series.filter((s) => visible.has(s.code)),
)

function pointsOf(s) {
  return byWeek(s)
    .filter(Boolean)
    .map((pt, i) => {
      const idx = props.chart.weeks.indexOf(pt.week)
      return `${x(idx)},${y(pt.score)}`
    })
    .join(' ')
}

function toggle(code) {
  visible.has(code) ? visible.delete(code) : visible.add(code)
}

function onMove(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const px = ((e.clientX - rect.left) / rect.width) * W
  // 找最近周
  let best = 0
  let bestD = Infinity
  props.chart.weeks.forEach((_, i) => {
    const d = Math.abs(x(i) - px)
    if (d < bestD) { bestD = d; best = i }
  })
  hoverIdx.value = best
}

const tipStyle = computed(() => {
  if (hoverIdx.value === null) return {}
  const pct = (x(hoverIdx.value) / W) * 100
  return { left: `${pct}%`, transform: hoverIdx.value === 0 ? 'translateX(8px)' : 'translateX(calc(-100% - 12px))' }
})

function fmt(pt) {
  if (!pt) return '—'
  return `${pt.raw} / T${pt.score}`
}

// 默认全选;图表数据异步到达后补齐
watch(
  () => props.chart.series,
  (s) => s.forEach((x) => visible.add(x.code)),
  { immediate: true },
)
</script>

<style scoped>
.viz-root {
  color-scheme: light;
  --surface-1: #fcfcfb;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
}
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.legend { display: flex; flex-wrap: wrap; gap: 4px; }
.legend-item {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); background: #fff; border-radius: 999px;
  padding: 3px 10px; font-size: 12px; cursor: pointer; color: var(--ink-2);
}
.legend-item.off { opacity: .38; }
.swatch { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.plot-area { position: relative; width: 100%; }
.plot-svg { width: 100%; height: 320px; }
.grid { stroke: #eceae4; stroke-width: 1; }
.baseline { stroke: #d8d6ce; stroke-width: 1; stroke-dasharray: 4 3; }
.tick { font-size: 11px; fill: var(--ink-3); }
.axis-title { font-size: 11px; fill: var(--ink-3); }
.crosshair { stroke: #b9b7ae; stroke-width: 1; stroke-dasharray: 3 3; }
.tip {
  position: absolute; top: 30px;
  background: #fff; border: 1px solid var(--line); border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,.12); padding: 8px 12px; min-width: 150px;
  pointer-events: none; font-size: 12px;
}
.tip-head { font-weight: 700; margin-bottom: 4px; }
.tip-row { display: flex; align-items: center; gap: 6px; padding: 2px 0; }
.tip-name { color: var(--ink-2); flex: 1; }
.tip-val { font-variant-numeric: tabular-nums; color: var(--ink); }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid var(--line); padding: 6px 8px; text-align: center; }
.data-table th { background: #f7f6f2; color: var(--ink-2); font-weight: 600; }
</style>
