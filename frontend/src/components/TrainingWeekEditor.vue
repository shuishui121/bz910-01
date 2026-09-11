<template>
  <div>
    <h3>每周训练内容</h3>
    <div class="row" style="align-items:flex-end">
      <label class="field" style="width:110px">训练周次
        <input v-model.number="form.week_no" type="number" min="1" max="53" class="input" />
      </label>
      <label class="field" style="width:170px">该周周一日期
        <input v-model="form.training_date" type="date" class="input" />
      </label>
      <button class="btn" @click="loadWeek">读取该周</button>
      <button class="btn primary" @click="save">保存周报</button>
      <span v-if="msg" class="small" style="color:var(--good);align-self:center">{{ msg }}</span>
    </div>

    <ItemEditor title="技术项" v-model="form.technical_items"
                :columns="[{key:'name',label:'动作',w:160},{key:'sets',label:'组数'},{key:'reps',label:'次数/时长'},{key:'note',label:'备注',w:200}]" />
    <ItemEditor title="体能项" v-model="form.physical_items"
                :columns="[{key:'name',label:'项目',w:160},{key:'load',label:'距离/负荷'},{key:'sets',label:'组数'},{key:'note',label:'备注',w:200}]" />

    <div class="sub">
      <div class="sub-head">
        <strong>对抗赛成绩</strong>
        <button class="btn small" @click="form.matches.push({name:'',score:'',result:'胜',note:''})">+ 添加比赛</button>
      </div>
      <div v-for="(m, i) in form.matches" :key="i" class="row match-row">
        <input v-model="m.name" class="input" placeholder="对手/赛事名" style="width:180px" />
        <input v-model="m.score" class="input" placeholder="比分 如 3:1" style="width:110px" />
        <select v-model="m.result" class="input" style="width:90px">
          <option>胜</option><option>负</option><option>平</option>
        </select>
        <input v-model="m.note" class="input" placeholder="备注" style="flex:1;min-width:160px" />
        <button class="btn small danger" @click="form.matches.splice(i,1)">删</button>
      </div>
      <div v-if="!form.matches.length" class="muted small">本周无对抗赛记录</div>
    </div>

    <label class="field" style="margin-top:12px">本周训练小结
      <textarea v-model="form.summary" class="input" placeholder="整体完成情况、亮点与问题…"></textarea>
    </label>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import http from '../api/http.js'
import ItemEditor from './ItemEditor.vue'

const props = defineProps({
  playerId: [String, Number],
  seasonYear: { type: Number, default: 2026 },
})

const monday = () => {
  const d = new Date()
  const wd = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - wd)
  return d.toISOString().slice(0, 10)
}

const form = reactive({
  week_no: 1,
  training_date: monday(),
  technical_items: [],
  physical_items: [],
  matches: [],
  summary: '',
})
const msg = ref('')
let timer
watch(msg, () => { clearTimeout(timer); timer = setTimeout(() => (msg.value = ''), 2500) })

async function loadWeek() {
  const list = await http.get(`/players/${props.playerId}/training-weeks`, {
    params: { season_year: props.seasonYear },
  })
  const found = list.find((w) => w.week_no === Number(form.week_no))
  if (!found) {
    Object.assign(form, { technical_items: [], physical_items: [], matches: [], summary: '' })
    msg.value = '该周尚无记录,可直接录入'
    return
  }
  Object.assign(form, {
    training_date: found.training_date,
    technical_items: found.technical_items || [],
    physical_items: found.physical_items || [],
    matches: found.matches || [],
    summary: found.summary || '',
  })
  msg.value = '已载入该周记录'
}

async function save() {
  await http.put(`/players/${props.playerId}/training-weeks`, form, {
    params: { season_year: props.seasonYear },
  })
  msg.value = '周报已保存'
}
</script>

<style scoped>
.sub { margin: 12px 0; border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
.sub-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.match-row { margin-bottom: 8px; }
</style>
