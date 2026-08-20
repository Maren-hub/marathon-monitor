<script setup>
import { computed } from 'vue'

const props = defineProps({
  segment: { type: Object, default: null }
})

const baseWeights = {
  S1: [75, 25],
  S2: [65, 35],
  S3: [50, 50],
  S4: [30, 70],
  S5: [45, 55]
}

const strategy = computed(() => {
  if (!props.segment) return null

  const [baseCrowd, baseHealth] = baseWeights[props.segment.id] ?? [50, 50]
  const riskDifference = (props.segment.crowd_risk - props.segment.health_risk) * 18
  const crowdWeight = Math.round(Math.min(85, Math.max(15, baseCrowd + riskDifference)))
  const healthWeight = 100 - crowdWeight

  const dominant = crowdWeight > healthWeight ? '人员聚集与通行秩序' : healthWeight > crowdWeight ? '身体安全与异常体征' : '聚集风险与身体安全协同'
  const reason = crowdWeight > healthWeight
    ? `当前处于${props.segment.name}，人员密度和通行冲突风险更值得优先关注。系统结合实时聚集风险，提升人群态势监测优先级。`
    : healthWeight > crowdWeight
      ? `当前处于${props.segment.name}，运动员体力消耗增大。系统结合实时健康风险，提升跌倒与异常体征监测优先级。`
      : `当前处于${props.segment.name}，系统对人员密度与身体安全保持均衡监测，并根据实时事件动态调整任务。`

  return {
    crowdWeight,
    healthWeight,
    dominant,
    reason,
    tasks: props.segment.monitoring_tasks ?? []
  }
})
</script>

<template>
  <section class="panel strategy-panel">
    <div class="panel-heading strategy-heading">
      <div>
        <span class="eyebrow">ADAPTIVE STRATEGY</span>
        <h2>智能监测策略</h2>
      </div>
      <span class="strategy-status"><i></i> 动态编排</span>
    </div>

    <template v-if="strategy">
      <div class="strategy-focus">
        <span>当前重点</span>
        <strong>{{ strategy.dominant }}</strong>
      </div>

      <div class="weight-grid">
        <div class="weight-item crowd-weight">
          <div><span>聚集监测</span><b>{{ strategy.crowdWeight }}%</b></div>
          <div class="weight-track"><i :style="{ width: `${strategy.crowdWeight}%` }"></i></div>
        </div>
        <div class="weight-item health-weight">
          <div><span>安全监测</span><b>{{ strategy.healthWeight }}%</b></div>
          <div class="weight-track"><i :style="{ width: `${strategy.healthWeight}%` }"></i></div>
        </div>
      </div>

      <div class="strategy-reason">
        <span>系统判断依据</span>
        <p>{{ strategy.reason }}</p>
      </div>

      <div class="strategy-tasks">
        <span>当前推荐任务</span>
        <div><b v-for="task in strategy.tasks" :key="task">{{ task }}</b></div>
      </div>
    </template>
  </section>
</template>
