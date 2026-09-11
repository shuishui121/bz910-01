<template>
  <div class="sub">
    <div class="sub-head">
      <strong>{{ title }}</strong>
      <button class="btn small" @click="addRow">+ 添加一行</button>
    </div>
    <div v-for="(_, i) in modelValue" :key="i" class="row item-row">
      <template v-for="col in columns" :key="col.key">
        <input v-model="modelValue[i][col.key]" class="input"
               :placeholder="col.label" :style="{ width: (col.w || 90) + 'px' }" />
      </template>
      <button class="btn small danger" @click="modelValue.splice(i, 1)">删</button>
    </div>
    <div v-if="!modelValue.length" class="muted small">暂无条目</div>
  </div>
</template>

<script setup>
const props = defineProps({
  title: String,
  modelValue: { type: Array, required: true },
  columns: { type: Array, required: true },
})

// 父级以 v-model 传入 reactive 数组,原地 push/splice 即可保持双向同步
function addRow() {
  props.modelValue.push(Object.fromEntries(props.columns.map((c) => [c.key, ''])))
}
</script>

<style scoped>
.sub { margin: 12px 0; border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
.sub-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.item-row { margin-bottom: 8px; }
</style>
