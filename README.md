# Cross-platform Test Studio

Cross-platform visual test authoring and deterministic execution for desktop, Android and iOS.

## Product capabilities

- A visual flow editor backed by versionable JSON assets
- Shared action and assertion vocabulary across platforms
- Desktop selectors using DOM/CDP, accessibility, OCR and image templates
- Android selectors using UI hierarchy, resource identifiers, text, OCR and templates
- iOS selectors using WDA hierarchy, accessibility identifiers, OCR and templates
- Explicit fallback policies instead of uncontrolled AI actions
- Dry run, step run, suite run, cancellation and debug bundles
- Screenshots, video, logs, timing and unified reports
- Optional AI assistance for element naming, draft generation and failure diagnosis

## Architecture

```text
Web authoring UI
      |
      v
Flow application service ---- asset repository
      |
      v
Shared flow runner
      |
  +---+-------------+
  |         |       |
Desktop   Android  iOS adapters
  |         |       |
CDP/A11y  ADB/UIA  WDA/A11y
```

AI may create or review a draft, but the saved flow and deterministic runner remain authoritative. Platform adapters implement a common driver contract so a team can replace Playwright, Appium, Airtest or WDA without rewriting flow assets.

## Planned public milestones

1. Portable Flow v1 schema and validation library
2. Demo Notes application for desktop and Android
3. Headless runner and HTML report
4. Visual authoring UI
5. Desktop/Android/iOS adapters and recovery policies

## Quick start

Run the dependency-free contract demo:

```bash
PYTHONPATH=src python -m test_studio.cli run examples/create-note.flow.json
```

Run the real desktop adapter:

```bash
python -m http.server 4173 --directory demo
python -m venv .venv && source .venv/bin/activate
pip install -e '.[desktop]'
playwright install chromium
test-studio run examples/create-note.playwright.flow.json --driver playwright --base-url http://127.0.0.1:4173
```

ADB and WDA adapters are selected with `--driver adb` and `--driver wda`. Device identifiers and application identifiers are always supplied at runtime.
