<script setup>
import { ref } from 'vue'
import { platformApi } from '../services/api'

defineProps({
  results: { type: Array, default: () => [] },
  selectedSegmentId: { type: String, default: '' }
})
const emit = defineEmits(['select', 'imported'])
const input = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const defaultStatus = ref('模拟')
const report = ref(null)
const failure = ref(null)
const names = { wearable: '手环', uav: '无人机', environment: '环境', gis_segments: '赛段 GIS' }

const percent = (value) => value == null ? '—' : `${Math.round(value * 100)}%`
const timeLabel = (value) => value ? value.slice(11, 19) : '—'
const missingLabel = (items) => items?.map((item) => names[item] ?? item).join('、') || ''

function openPicker() { if (!uploading.value) input.value?.click() }
function onDrop(event) {
  dragging.value = false
  uploadFile(event.dataTransfer?.files?.[0])
}
async function uploadFile(file) {
  if (!file) return
  report.value = null
  failure.value = null
  if (!/\.(xlsx|csv)$/i.test(file.name)) {
    failure.value = { message: '请选择 .xlsx 或 .csv 文件；旧版 .xls 请先另存为 .xlsx', issues: [] }
    return
  }
  if (file.size > 6 * 1024 * 1024) {
    failure.value = { message: '文件超过 6 MB，请分批导入', issues: [] }
    return
  }
  uploading.value = true
  try {
    report.value = await platformApi.importSpreadsheet(file, defaultStatus.value)
    emit('imported', report.value)
  } catch (error) {
    failure.value = { message: error.message, issues: error.issues ?? [] }
  } finally {
    uploading.value = false
    if (input.value) input.value.value = ''
  }
}
</script>

<template>
  <section class="panel pipeline-result-panel">
    <div class="panel-heading">
      <div><span class="eyebrow">AUTOMATIC PIPELINE</span><h2>接入数据</h2></div>
      <span class="live-mark"><i></i> AUTO</span>
    </div>
    <div class="upload-settings">
      <label for="source-status">缺少性质列时按</label>
      <select id="source-status" v-model="defaultStatus" :disabled="uploading"><option>模拟</option><option>公开</option><option>实测</option></select>
    </div>
    <div class="upload-dropzone" :class="{ dragging, uploading }" role="button" tabindex="0"
      @click="openPicker" @keydown.enter.prevent="openPicker" @keydown.space.prevent="openPicker"
      @dragenter.prevent="dragging = true" @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="onDrop">
      <input ref="input" type="file" accept=".xlsx,.csv" hidden @click.stop @change="uploadFile($event.target.files?.[0])">
      <strong>{{ uploading ? '正在读取并检查表格…' : '拖入 Excel 表格，或点击选择文件' }}</strong>
      <span>支持 .xlsx / .csv · 不超过 6 MB · 请先去除姓名和联系方式</span>
    </div>
    <details class="upload-fields">
      <summary>查看表格格式与必填字段</summary>
      <p>第一行放列名；可以只有一种数据，也可以在同一 Excel 中分四个工作表。中英文列名均可。</p>
      <p><b>手环：</b>采集时间、设备编号、运动员编号、赛段编号、已完成距离、当前速度、心率、血氧</p>
      <p><b>无人机：</b>采集时间、设备编号、赛段编号、人数、观测面积、平均速度</p>
      <p><b>环境：</b>采集时间、设备编号、赛段编号、温度、湿度、风速</p>
      <p><b>赛段 GIS：</b>赛段编号、起点里程、终点里程、道路宽度、平均坡度、最大坡度、弯道等级、救援通达性、最近医疗点距离</p>
      <p>时间最好使用 Excel 日期时间或“2026-10-10 09:30:00”；赛段编号如 S1。单位依次为 km、m/s、bpm、%、m²、℃、m。数据字典本身不是采集数据表。</p>
    </details>
    <div v-if="failure" class="import-feedback error" role="alert">
      <strong>{{ failure.message }}</strong>
      <ul v-if="failure.issues.length"><li v-for="(issue, index) in failure.issues" :key="index">{{ issue }}</li></ul>
    </div>
    <div v-else-if="report" class="import-feedback success" role="status">
      <strong>已导入：{{ report.filename }}</strong>
      <span>{{ Object.entries(report.accepted).map(([key, count]) => `${names[key]} ${count} 行`).join(' · ') }}</span>
      <span>可计算赛段：{{ report.usable_segments.join('、') || '暂无' }}</span>
      <span v-if="report.partial_segments.length">待补齐：{{ report.partial_segments.map((item) => `${item.segment_id} 缺${missingLabel(item.missing_sources)}`).join('；') }}</span>
    </div>
    <div v-if="results.length" class="pipeline-result-list">
      <button v-for="item in results" :key="`${item.window_start}-${item.segment_id}`" class="pipeline-result-card"
        :class="{ selected: selectedSegmentId === item.segment_id, partial: item.record_status !== 'usable' }" @click="emit('select', item.segment_id)">
        <div class="pipeline-result-title"><strong>{{ item.segment_id }} · {{ item.focus_label || '数据待补齐' }}</strong><span>{{ timeLabel(item.window_start) }}</span></div>
        <div v-if="item.record_status === 'usable'" class="pipeline-risk-pair">
          <span>聚集 <b class="crowd-value">{{ percent(item.crowd_risk) }}</b></span>
          <span>健康 <b class="health-value">{{ percent(item.health_risk) }}</b></span>
          <span>置信度 <b>{{ percent(item.data_confidence) }}</b></span>
        </div>
        <p v-else class="pipeline-missing">还缺：{{ missingLabel(item.missing_sources) }}。暂不参与风险计算。</p>
        <div class="pipeline-units"><span v-for="unit in item.recommended_units" :key="unit">{{ unit }}</span></div>
      </button>
    </div>
    <div v-else class="pipeline-empty"><strong>尚未导入采集数据</strong><span>拖入表格后，系统会校验并送入原有的数据处理管道。单一来源可以先导入，补齐四类数据后才生成完整风险。</span></div>
    <small class="pipeline-scope-note">导入会更新赛段风险与任务建议，不会自动生成真实报警或替换模拟运动员。数据暂存内存，后端重启后需重新导入。</small>
  </section>
</template>
