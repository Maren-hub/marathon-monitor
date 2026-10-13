<script setup>
defineEmits(['return-home', 'enter-dashboard'])
const docs = [
  { title: '平台总体架构', description: '系统模块、前后端与数据流说明', slug: 'architecture' },
  { title: '自动数据处理管道', description: '接入字段、融合规则与风险计算原型', slug: 'pipeline' },
  { title: '校园路线接入说明', description: 'QGIS 绘制、GeoJSON 导出与平台导入', slug: 'campus-route' },
  { title: '三维模型导入说明', description: '3D Tiles、原始 OSGB 压缩包与模型切换', slug: 'model-import' }
]
</script>

<template>
  <div class="help-page">
    <header><div><small>智跑慧巡 / HELP CENTER</small><h1>帮助中心</h1><p>先按操作指南完成一次模拟推演，再查看参数和技术文档。</p></div><nav><button @click="$emit('return-home')">返回首页</button><button class="primary" @click="$emit('enter-dashboard')">进入监控平台</button></nav></header>
    <main>
      <section><span class="eyebrow">01 / 操作指南</span><h2>用五步看懂平台</h2><div class="guide-grid">
        <article><b>01</b><h3>进入看板</h3><p>从首页点击“进入平台演示”，查看赛段、风险、无人机与实时事件。</p></article>
        <article><b>02</b><h3>运行推演</h3><p>点击底部“开始自动演示”。系统会按时间推进，依次出现聚集、跌倒和体征异常等模拟事件。</p></article>
        <article><b>03</b><h3>查看事件</h3><p>选中赛段，观察重点监测任务变化；在右侧事件卡片里确认、派遣和完成处置。</p></article>
        <article><b>04</b><h3>导入表格</h3><p>顶部切换“接入数据”，在右侧选择数据性质并拖入 .xlsx 或 .csv。若只导入一种来源，面板会显示还缺哪些数据。</p></article>
        <article><b>05</b><h3>复盘并导出</h3><p>使用顶部“赛事复盘”查看闭环情况，点击“导出成果”下载 CSV、JSON 和 HTML 报告压缩包。</p></article>
      </div></section>
      <section><span class="eyebrow">02 / 参数说明</span><h2>这些数字是什么意思</h2><div class="term-grid">
        <article><h3>聚集风险 / 健康风险</h3><p>0–1 的规则化相对指标，越接近 1 表示越值得优先查看；不是经过临床或真实赛事标定的概率。</p></article>
        <article><h3>监测重点</h3><p>依据赛段阶段和实时风险，在人群通行、个体安全、综合监测之间切换，作为任务建议。</p></article>
        <article><h3>人群热力 / 健康热力</h3><p>按五个逻辑赛段的汇总值绘制示意区域，不能当成某个具体路口的实测热力分布。</p></article>
        <article><h3>无人机覆盖区</h3><p>以无人机当前位置绘制固定半径的演示圈，尚未考虑真实相机视场角、遮挡、航高和禁飞要求。</p></article>
        <article><h3>接入数据</h3><p>可拖入包含手环、无人机、环境和赛段 GIS 数据的 .xlsx 或 .csv。表格按行检查，整表通过后写入内存管道。仅数据齐全的赛段会覆盖模拟风险，其余赛段回退模拟值。</p></article>
        <article><h3>校园三维实景</h3><p>已加载校园倾斜摄影模型。旧截图拟合线路已撤下；由同伴在 QGIS 画线并导入 GeoJSON。逻辑赛事数据通过 S1—S5 与校园线路建立演示映射。</p></article>
        <article><h3>三维模型导入</h3><p>地图上方可打开独立窗口，切换现有模型或上传完整 ZIP。原始 OSGB 需在后台转换成 3D Tiles，上传不等于已成功显示。</p></article>
      </div></section>
      <section><span class="eyebrow">03 / 技术资料</span><h2>技术文档</h2><div class="doc-grid"><a v-for="doc in docs" :key="doc.slug" :href="`/api/technical-docs/${doc.slug}`" download><strong>{{ doc.title }}</strong><span>{{ doc.description }}</span><b>下载 Markdown 文档 ↗</b></a></div></section>
    </main>
  </div>
</template>

<style scoped>
.help-page { height: 100%; overflow: auto; color: #eaf7fa; background: #06131d; }
header { display: flex; justify-content: space-between; align-items: start; gap: 25px; padding: 50px clamp(24px, 6vw, 100px); border-bottom: 1px solid #1b3b4e; background: radial-gradient(circle at 70% 30%, #113b4d, #071b2a 55%); }
header small, .eyebrow { color: #54d9d1; font-size: 11px; letter-spacing: .17em; } h1 { margin: 12px 0; font-size: 46px; } header p, article p { color: #9fb9c4; line-height: 1.7; } nav { display: flex; gap: 9px; } button { padding: 10px 15px; border: 1px solid #3a6e81; border-radius: 7px; color: #ddf5f7; background: #123247; cursor: pointer; white-space: nowrap; } button.primary { color: #092733; background: #6be4d8; }
main { max-width: 1350px; margin: auto; padding: 0 24px 80px; } section { margin-top: 65px; } h2 { margin: 12px 0 25px; font-size: 27px; } .guide-grid, .term-grid, .doc-grid { display: grid; gap: 13px; } .guide-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }.term-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }.doc-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } article, .doc-grid a { min-width: 0; padding: 19px; border: 1px solid #22495a; border-radius: 12px; background: #0a2433; } article b { color: #5be3d6; } h3 { font-size: 15px; } article p { margin-bottom: 0; font-size: 12px; }.doc-grid a { display: grid; gap: 11px; color: #eaf7fa; text-decoration: none; }.doc-grid a:hover { border-color: #65ded8; }.doc-grid span { color: #9bb7c2; font-size: 12px; }.doc-grid b { color: #62dcd7; font-size: 11px; }
@media (max-width: 950px) { .guide-grid { grid-template-columns: repeat(2, 1fr); }.term-grid,.doc-grid { grid-template-columns: repeat(2, 1fr); } } @media (max-width: 600px) { header { display: block; } nav { margin-top: 20px; }.guide-grid,.term-grid,.doc-grid { grid-template-columns: 1fr; } }
</style>
