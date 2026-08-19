# 马拉松智能监控平台原型

这是一个面向大创比赛的初步平台骨架，使用：

- **FastAPI / Python**：后台接口、模拟器、风险计算和实时推送；
- **Vue 3 / Vite**：监控平台界面；
- **CesiumJS**：三维赛道、运动员和无人机显示；
- **WebSocket**：每秒推送一次平台状态；
- **PostgreSQL/PostGIS、MQTT、AI识别**：已规划为下一阶段扩展，本版本尚未强制依赖。

## 当前已经实现

- 五段式42.195公里逻辑赛道；
- 36名匿名模拟运动员及心率、配速和位置；
- 两架模拟无人机及电量、任务和位置；
- 每个赛段的聚集风险、健康风险和监测重点；
- 聚集优先、个体安全优先、综合监测三种任务模式；
- 模拟聚集、跌倒、体征异常；
- 报警展示、定位和确认处置；
- 模拟推演的暂停、继续和重置；
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
├─ docs/architecture.md   # 架构与后续扩展说明
├─ scripts/               # Windows安装和启动脚本
└─ app.py                 # 后端快捷入口
```

## 首次运行前

Windows电脑需要安装：

1. Python 3.12或3.13，安装时勾选 **Add Python to PATH**；
2. 当前 Node.js LTS；
3. 推荐使用 Visual Studio Code。

打开 PowerShell，进入本项目目录后运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

该脚本会在项目内创建 `.venv`，并安装后端与前端依赖。

## 启动平台

打开第一个PowerShell窗口：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-backend.ps1
```

打开第二个PowerShell窗口：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-frontend.ps1
```

访问：

- 平台界面：<http://127.0.0.1:5173>
- FastAPI接口文档：<http://127.0.0.1:8000/docs>
- 后端健康检查：<http://127.0.0.1:8000/api/health>

## 演示方法

1. 在左侧选择一个赛段；
2. 观察聚集风险、健康风险和当前监测重点；
3. 点击底部“模拟聚集”“模拟跌倒”或“模拟体征异常”；
4. 查看该赛段风险与监测任务自动变化；
5. 查看无人机任务变化和右侧报警；
6. 点击报警定位赛段并确认处置。

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

