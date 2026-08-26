# Cross-platform Test Studio｜跨端 UI 自动化执行引擎

[English summary](#english-summary)

面向桌面端、Android 和 iOS 的统一自动化 Flow 协议与确定性执行引擎。它解决的是“一条业务场景如何跨平台复用，同时保留各端真实交互差异”，而不是把三套脚本简单拼在一起。

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

> 当前仓库的重点是 Flow 协议和执行内核。完整的拖拽式可视化编排器、设备画面投屏及录制并未作为已完成功能提供。

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

Cross-platform Test Studio provides a versionable Flow v1 contract and deterministic runner shared by desktop, Android, and iOS automation. It supports multiple assertions per action, explicit selector fallbacks, simulation and platform drivers, and failure evidence. The current public version focuses on the execution core rather than a full visual authoring product.

## License

MIT
