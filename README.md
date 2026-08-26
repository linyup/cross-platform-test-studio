# Cross-platform Test Studio｜跨端 UI 自动化执行引擎

[English summary](#english-summary)

面向桌面端、Android 和 iOS 的统一自动化 Flow 协议与确定性执行引擎。它解决的是“一条业务场景如何跨平台复用，同时保留各端真实交互差异”，而不是把三套脚本简单拼在一起。

## 工程实践界面

> **版本说明：** 下列截图来自实际项目中持续使用的完整工程实践版本，并非当前仓库启动后的界面截图。开源仓库提供独立实现的 Flow 编排器、Portable Flow 协议、Runner 和基础 Driver，用于复现核心设计与执行闭环；截图中的完整元素采集、真实设备投屏、录屏报告及企业平台集成不在开源范围内。

公开版编排器支持编辑场景、步骤、定位策略和多个校验点，并直接调用同一仓库中的公开版 Runner。它保留实际项目的设计思路，但不等同于生产平台的完整前后端版本。

### PC 元素采集

PC 端通过 CDP 连接桌面应用或浏览器，按目标技术条件选择视觉采集或 DOM 点选采集。视觉模式支持截取最大化窗口、框选区域并生成图片模板。

![CDP 已连接后的图片模板采集](docs/assets/pc-visual-capture.png)

点选模式直接在目标应用中选择真实元素，保留操作上下文。

![在目标应用中点选元素](docs/assets/pc-point-select.png)

当文案或结构不能唯一定位时，采集器列出候选节点和定位策略，由测试人员确认后再生成代码，避免运行时盲选。

![点选采集后的候选定位方案](docs/assets/pc-candidate-locators.png)

### PC 执行报告与录屏

执行完成后由 Allure 汇总套件、场景、步骤、子步骤、状态和耗时，并将本次屏幕录制作为报告附件嵌入。测试人员可以从失败步骤直接回看操作现场，结合日志和截图定位问题。

![包含执行步骤和屏幕录制的 PC 自动化报告](docs/assets/pc-allure-video-report.png)

### 场景编排

通过组件组合业务步骤，支持单步调试、断言、等待、变量、历史版本和 AI 场景审查。

![移动端自动化场景编排](docs/assets/flow-authoring.png)

### 元素资产管理

图片模板、OCR 和结构化控件统一入库，定位策略、搜索区域、阈值及引用关系作为可版本化资产维护。

![元素资产管理](docs/assets/element-library.png)

### 连接设备后的采集

连接 Android 或 iOS 设备后，可从实时画面截图、拉取控件树，并将选择结果沉淀为元素资产。

![连接设备后的元素采集](docs/assets/device-capture.png)

## 核心设计

- 业务意图使用同一套 Portable Flow v1 表达，并以 JSON 保存，便于版本管理和评审。
- 每个操作后可以配置多个预期结果，避免把校验点错误统计成操作步骤。
- 各平台使用显式定位器和降级顺序，运行时不会让 AI 随机寻找元素。
- Runner 与 Driver 解耦，同一条 Flow 可切换模拟、Playwright、ADB 或 WDA 驱动。
- 失败时保存截图及驱动侧证据，统一生成步骤级执行结果。

## 当前已实现

- Portable Flow v1 数据模型、校验和命令行入口
- 通用 `FlowRunner`，支持执行、断言、失败策略和取消检查
- 一个操作对应多个断言
- 显式 selector fallback
- 确定性模拟驱动，适合协议测试和 CI
- Playwright 桌面端驱动及真实 Chrome CDP 冒烟示例
- ADB Android 与 WDA iOS 基础驱动接口
- 失败截图和 JSON 结果产物
- 可直接运行的 Notes Web 示例应用
- 可直接运行的浏览器编排器，支持步骤增删改、多个预期、JSON 编辑、撤销/重做、保存和模拟执行

## 架构

```mermaid
flowchart LR
    A["Portable Flow v1<br/>JSON 资产"] --> B["模型校验与标准化"]
    B --> C["FlowRunner<br/>步骤、断言、失败策略"]
    C --> D{"Driver Contract"}
    D --> E["Simulation<br/>CI 与协议测试"]
    D --> F["Playwright / CDP<br/>桌面端"]
    D --> G["ADB / UI Hierarchy<br/>Android"]
    D --> H["WDA / Accessibility<br/>iOS"]
    E --> I["统一执行结果"]
    F --> I
    G --> I
    H --> I
    I --> J["截图、错误与步骤证据"]
```

## 快速开始

运行不依赖浏览器和设备的模拟示例：

```bash
PYTHONPATH=src python -m test_studio.cli run examples/create-note.flow.json
```

启动可视化编排器：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
test-studio serve --flow examples/create-note.flow.json
```

打开 `http://127.0.0.1:4174`。页面修改会保存回传入的 Flow 文件，“运行”使用同一套 Python `FlowRunner` 和确定性模拟 Driver，不是静态界面演示。

运行真实桌面端示例：

```bash
python -m http.server 4173 --directory demo
python -m venv .venv
source .venv/bin/activate
pip install -e '.[desktop]'
playwright install chromium
test-studio run examples/create-note.playwright.flow.json \
  --driver playwright \
  --base-url http://127.0.0.1:4173
```

Android 和 iOS 分别通过 `--driver adb`、`--driver wda` 选择驱动，设备标识与应用标识均在运行时传入。

## 与其他项目的关系

- [quality-ai-skills](https://github.com/linyup/quality-ai-skills)：从需求或人工用例生成 Flow 草稿。
- [device-test-lab](https://github.com/linyup/device-test-lab)：调度设备和执行 Agent，调用本项目 Runner 完成任务。

## English summary

Cross-platform Test Studio provides a versionable Flow v1 contract, a deterministic runner, and a runnable visual authoring workspace shared by desktop, Android, and iOS automation. It supports multiple assertions per action, explicit selector fallbacks, simulation and platform drivers, and failure evidence.

## License

MIT
