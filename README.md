# 马拉松智能监控平台原型

这是一个面向大创比赛的可运行平台原型。仓库包含完整前端、后端、合成赛事数据、测试、启动脚本和设计说明。

- **FastAPI / Python**：后台接口、模拟器、风险计算和实时推送；
- **Vue 3 / Vite**：监控平台界面；
- **CesiumJS**：三维赛道、运动员和无人机显示；
- **WebSocket**：每秒推送一次平台状态；
- **PostgreSQL/PostGIS、MQTT、AI识别**：已规划为下一阶段扩展，本版本尚未强制依赖。

## 当前已经实现

- 五段式42.195公里逻辑赛道；
- 120名匿名模拟运动员及位置、配速、心率、血氧和疲劳度；
- 地图点击运动员查看个人数字档案和风险状态；
- 两架模拟无人机及电量、任务、预计到达时间和模拟监控画面；
- 跌倒事件触发无人机紧急调度和近距目标跟踪；
- 每个赛段的聚集风险、健康风险和监测重点；
- 分赛段动态监测权重、系统判断依据和推荐任务；
- 赛道绿、黄、橙、红四级风险着色及紧急报警闪烁；
- 模拟聚集、跌倒、体征异常；
- 无人机复核、医疗救援、现场疏导和完成处置闭环；
- 报警负责单位、首次响应时间和完整处置时间记录；
- 赛事事件、处置效率、无人机调度和分赛段历史峰值复盘；
- 可通过浏览器打印功能将赛事复盘保存为PDF；
- 模拟推演的暂停、继续和重置，重置后停在起点等待开始；
- 从 `data/demo_scenario.json` 读取赛事名称、人数、天气、速度和赛段风险；
- FastAPI自动接口文档和基础测试。

## 目录结构

```text
marathon monitor/
├─ backend/
│  ├─ app/
│  │  ├─ main.py          # FastAPI入口与接口
│  │  ├─ schemas.py       # 前后端数据结构
│  │  └─ simulation.py    # 模拟数据与风险任务逻辑
│  ├─ tests/              # 后端接口测试
│  └─ requirements*.txt
├─ frontend/
│  ├─ src/components/     # 地图、赛段、报警和控制组件
│  ├─ src/composables/    # 实时连接逻辑
│  ├─ src/services/       # 后端接口封装
│  └─ package.json
├─ data/demo_scenario.json # 可编辑的合成赛事配置
├─ docs/                  # 架构、个人任务书和团队协作说明
├─ scripts/               # Windows安装和启动脚本
└─ app.py                 # 后端快捷入口
```

## 新电脑首次下载

在准备存放项目的目录打开 PowerShell，逐条运行：

```powershell
git clone https://github.com/Maren-hub/marathon-monitor.git
cd marathon-monitor
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

不要一次把多条命令粘贴到同一行。每条命令执行完成后再执行下一条。

## 首次运行前

Windows电脑需要安装：

1. Python 3.11或更新版本，安装时勾选 **Add Python to PATH**；
2. 当前 Node.js LTS；
3. Git for Windows；
4. 推荐使用 Visual Studio Code。

打开 PowerShell，进入本项目目录后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

该脚本会在项目内创建 `.venv`，并安装后端与前端依赖。

## 启动平台

打开第一个PowerShell窗口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

打开第二个PowerShell窗口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

访问：

- 平台界面：<http://127.0.0.1:5173>
- FastAPI接口文档：<http://127.0.0.1:8000/docs>
- 后端健康检查：<http://127.0.0.1:8000/api/health>

## 演示方法

推荐使用自动演示：

1. 点击页面底部“开始自动演示”；
2. 系统会自动重置赛事，并按约 6 分钟时间线依次展示起跑、局部拥挤、中程、跌倒、后程体征异常、终点聚集和赛事结束；
3. 页面会显示演示进度、当前场景和下一事件倒计时，并自动定位到对应赛段；
4. 演示过程中可以暂停和继续；演示结束后可点击“重新自动演示”。

也可以手动演示：

1. 在左侧选择一个赛段；
2. 观察聚集风险、健康风险和当前监测重点；
3. 点击底部“模拟聚集”“模拟跌倒”或“模拟体征异常”；
4. 查看该赛段风险与监测任务自动变化；
5. 查看无人机任务变化和右侧报警；
6. 根据事件类型选择无人机复核、派遣医疗或现场疏导，并完成处置；
7. 点击顶部“赛事复盘”查看统计结果，需要时打印或保存为PDF。

若要修改赛事名称、模拟人数、天气和演示时间线，请编辑 `data/demo_scenario.json`，保存后在平台点击“重置”重新载入。

这能直接展示项目的核心想法：系统不是全程采用相同监测方式，而是根据赛段状态自动决定当前重点监测什么。

## 后端测试

安装完成后，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

## 下一阶段建议

1. 用真实校园赛道GeoJSON替换当前模拟坐标；
2. 将倾斜摄影模型转换为3D Tiles并加载到Cesium；
3. 增加PostgreSQL/PostGIS数据库；
4. 编写MQTT接入服务，先连接手机或一个ESP32手环；
5. 将离线无人机视频的跌倒/聚集识别结果接入事件接口；
6. 把当前规则型风险计算升级为可实验对比的任务编排模型；
7. 加入事件回放和救援路径规划。

架构细节见 [docs/architecture.md](docs/architecture.md)。

## 团队协作

目前尚未确定成员分工，因此所有成员先完成“克隆、安装、启动、测试”即可，暂时不要直接修改 `main`。确定分工后再为每项任务建立独立分支并通过 Pull Request 合并。

详细步骤见 [团队协作与新电脑运行指南](docs/团队协作与新电脑运行指南.md)。
