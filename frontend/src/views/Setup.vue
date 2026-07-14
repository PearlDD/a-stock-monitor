<template>
  <div class="setup">
    <van-nav-bar title="配置指南" left-arrow @click-left="$router.back()" />

    <van-steps :active="activeStep" direction="vertical">
      <van-step v-for="step in guide.steps" :key="step.step">
        <div class="step-title">{{ step.title }}</div>
        <div class="step-desc">{{ step.description }}</div>
      </van-step>
    </van-steps>

    <van-cell-group title="注意事项" inset style="margin-top: 12px;">
      <van-cell v-for="(note, idx) in guide.notes" :key="idx" :title="note" />
    </van-cell-group>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSetupGuide } from '../api'

const guide = ref({ steps: [], notes: [] })
const activeStep = ref(0)

onMounted(async () => {
  try {
    const { data } = await getSetupGuide()
    guide.value = data
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.setup { padding-top: 8px; }
.step-title { font-size: 16px; font-weight: 600; }
.step-desc { font-size: 14px; color: #666; margin-top: 4px; }
</style>
