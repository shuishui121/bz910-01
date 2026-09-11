<template>
  <div>
    <div class="row" style="justify-content:space-between;align-items:center">
      <h3 style="margin:0">月度评语</h3>
      <div class="small muted">赛季 {{ seasonYear }} 年</div>
    </div>

    <div v-for="c in comments" :key="c.month" class="comment-item">
      <div class="row" style="justify-content:space-between">
        <strong>{{ c.month }} 月评语
          <span class="tag gray">{{ c.coach_name }} · v{{ c.version }}</span>
        </strong>
        <button v-if="canWrite" class="btn small" @click="edit(c)">编辑</button>
      </div>
      <p class="content">{{ c.content }}</p>
    </div>
    <div v-if="!comments.length" class="muted small">本赛季暂无评语</div>

    <hr v-if="canWrite" style="border:none;border-top:1px solid var(--line);margin:16px 0" />

    <div v-if="canWrite" class="editor">
      <label class="field">月份
        <select v-model.number="form.month" class="input" style="width:120px">
          <option v-for="m in 12" :key="m" :value="m">{{ m }} 月</option>
        </select>
      </label>
      <label class="field">评语内容
        <textarea v-model="form.content" class="input"
                  placeholder="本月技术、体能、态度、对抗赛表现与下月重点…"></textarea>
      </label>
      <div class="row" style="align-items:center">
        <button class="btn primary" :disabled="saving" @click="save">
          {{ saving ? '提交中…' : `提交评语（基于 v${form.base_version ?? 0}）` }}
        </button>
        <button v-if="editingId" class="btn" @click="reset">取消编辑</button>
        <span v-if="msg" class="small" :style="{color: okMsg ? 'var(--good)' : 'var(--serious)'}">{{ msg }}</span>
      </div>
    </div>

    <!-- 并发冲突弹窗 -->
    <div v-if="conflict" class="modal-mask" @click.self="conflict = null">
      <div class="card modal">
        <h3 style="color:var(--serious)">⚠ 评语版本冲突</h3>
        <p class="small">
          你编辑期间，<b>{{ conflict.current_coach_name || '另一位教练' }}</b>
          已提交了新版本（v{{ conflict.current_version }}）。请选择处理方式：
        </p>
        <div class="row conflict-cols">
          <div>
            <div class="small muted">对方当前版本</div>
            <textarea class="input" readonly :value="conflict.current_content"></textarea>
          </div>
          <div>
            <div class="small muted">我提交的内容</div>
            <textarea class="input" readonly :value="conflict.submitted_content"></textarea>
          </div>
        </div>
        <div v-if="mode === 'merge'">
          <div class="small muted">合并后的内容（可在双方文本基础上修改）</div>
          <textarea v-model="merged" class="input" style="min-height:140px"></textarea>
        </div>
        <div class="row" style="justify-content:flex-end;margin-top:12px">
          <button class="btn" @click="conflict = null">取消</button>
          <button class="btn danger" @click="resolve('overwrite')">用我的覆盖</button>
          <button class="btn primary" @click="startMerge">合并后提交</button>
          <button v-if="mode === 'merge'" class="btn primary" @click="resolve('merge')">
            确认合并提交
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api/http.js'

const props = defineProps({
  playerId: [String, Number],
  seasonYear: { type: Number, default: 2026 },
  canWrite: Boolean,
})

const comments = ref([])
const saving = ref(false)
const msg = ref('')
const okMsg = ref(false)
const editingId = ref(null)
const conflict = ref(null)
const mode = ref('choose')
const merged = ref('')

const form = reactive({ month: new Date().getMonth() + 1, content: '', base_version: null })

onMounted(load)

async function load() {
  comments.value = await http.get(`/players/${props.playerId}/comments`, {
    params: { season_year: props.seasonYear },
  })
}

function edit(c) {
  form.month = c.month
  form.content = c.content
  form.base_version = c.version
  editingId.value = c.id
  msg.value = ''
}
function reset() {
  form.content = ''
  form.base_version = null
  editingId.value = null
}

async function save() {
  saving.value = true
  msg.value = ''
  try {
    await http.put(`/players/${props.playerId}/comments`, {
      season_year: props.seasonYear,
      month: form.month,
      content: form.content,
      base_version: form.base_version,
    })
    okMsg.value = true
    msg.value = '评语已提交'
    reset()
    await load()
  } catch (e) {
    if (e.code === 40901) {
      conflict.value = e.data
      mode.value = 'choose'
    } else {
      okMsg.value = false
      msg.value = e.message
    }
  } finally {
    saving.value = false
  }
}

function startMerge() {
  mode.value = 'merge'
  merged.value =
    `${conflict.value.current_content}\n\n———— 合并分隔 ————\n\n${conflict.value.submitted_content}`
}

async function resolve(action) {
  await http.post(`/players/${props.playerId}/comments/resolve`, {
    season_year: props.seasonYear,
    month: form.month,
    content: conflict.value.submitted_content,
    action,
    merged_content: action === 'merge' ? merged.value : null,
  })
  conflict.value = null
  reset()
  await load()
}
</script>

<style scoped>
.comment-item { padding: 10px 0; border-bottom: 1px dashed var(--line); }
.content { white-space: pre-wrap; margin: 6px 0 0; color: var(--ink-2); line-height: 1.7; }
.editor { margin-top: 6px; }
.modal-mask {
  position: fixed; inset: 0; background: rgba(15,20,30,.45);
  display: grid; place-items: center; z-index: 50;
}
.modal { width: 760px; max-width: 92vw; max-height: 88vh; overflow-y: auto; }
.conflict-cols { align-items: stretch; }
.conflict-cols > div { flex: 1; min-width: 260px; }
.conflict-cols textarea { min-height: 150px; background: #faf9f6; }
</style>
