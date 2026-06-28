# CloakBrowser Manager 本地 APP 实施方案

## 目标

把当前的 FastAPI 后台和 React 前台封装成一个本地运行的小型桌面 APP，用它直接管理 CloakBrowser profiles，并负责启动、停止每个 profile 对应的 CloakBrowser 窗口。

完成后，日常使用方式应从两步：

```bash
uvicorn backend.main:app --reload --port 8080
cd frontend && npm run dev
```

变成一步：

```bash
open "CloakBrowser Manager.app"
```

APP 自己完成：

- 启动本地 FastAPI 后台。
- 加载已有 React 生产版前端。
- 使用当前项目的数据目录、缓存目录和 CloakBrowser Chromium。
- 在 APP 退出时停止后台，并触发现有 `browser_mgr.cleanup_all()` 清理正在运行的 profile。

## 调查结论

可以做，而且当前项目已经很接近本地 APP 形态。

现有系统本质上已经有本地服务内核：

- 后台是 FastAPI，入口是 `backend/main.py`。
- 前台是 React + Vite，生产构建目录是 `frontend/dist`。
- FastAPI 已经在 `frontend/dist` 存在时直接服务 React SPA。
- profile 数据存在 SQLite，默认 `DATA_DIR=~/.cloakbrowser-manager`，当前 `start.sh` 已经改成项目本地 `DATA_DIR=$PWD/data`。
- CloakBrowser 启动、停止、运行状态和 CDP 端口管理已经封装在 `backend/browser_manager.py`。
- 前端 API 客户端全部使用相对路径 `/api/...`，适合放进桌面 WebView，不需要重写前端。

推荐方案是：

```text
pywebview 本地窗口
  -> 启动 uvicorn/FastAPI
  -> FastAPI 服务 React dist + /api
  -> BrowserManager 启停 CloakBrowser
```

不推荐优先用 Electron。Electron 会引入第二套桌面运行时和 Node 打包链，体积更大，也不能减少 Python 后台。Tauri 可以做，但仍要把 Python 后台做 sidecar，复杂度比 `pywebview` 高。

## 已核实的现状

### 后台能力

`backend/main.py` 已有完整 API：

- `GET /api/profiles`：列出 profiles。
- `POST /api/profiles`：创建 profile。
- `GET /api/profiles/{profile_id}`：读取 profile。
- `PUT /api/profiles/{profile_id}`：更新 profile。
- `DELETE /api/profiles/{profile_id}`：删除 profile，运行中会先 stop。
- `POST /api/profiles/{profile_id}/launch`：启动 CloakBrowser profile。
- `POST /api/profiles/{profile_id}/stop`：停止 profile。
- `GET /api/profiles/{profile_id}/status`：查询 profile 状态。
- `GET /api/status`：查询系统状态。
- `/api/profiles/{profile_id}/cdp...`：CDP HTTP 和 WebSocket 代理。

`backend/browser_manager.py` 已有：

- 每个 profile 一个独立 `user_data_dir`。
- `launch_persistent_context_async(...)` 启动 CloakBrowser。
- `stop(profile_id)` 停止运行中的 context。
- `cleanup_all()` 关闭所有运行中的 profile。
- `auto_launch_all()` 启动 `auto_launch=True` 的 profiles。
- CDP 端口在 `5100-5199` 之间轮转，避免 TIME_WAIT 冲突。

### 前端能力

`frontend/src/lib/api.ts` 使用相对 API 路径：

```ts
request<Profile[]>("/api/profiles")
request<LaunchResult>(`/api/profiles/${id}/launch`, { method: "POST" })
request<{ ok: boolean }>(`/api/profiles/${id}/stop`, { method: "POST" })
```

这意味着 WebView 加载 `http://127.0.0.1:<port>` 后，前端无需知道真实端口，也无需额外配置 API base URL。

`frontend/src/hooks/useProfiles.ts` 已经每 3 秒刷新 profile 状态。APP 壳不需要新增状态轮询。

`frontend/src/components/LaunchButton.tsx` 和 `ProfileViewer.tsx` 已经提供启动、停止、复制 CDP URL 的 UI。

### 本机验证结果

已验证：

```bash
.venv/bin/python -c "import backend.main as m; print('backend import ok')"
```

结果：

```text
backend import ok
```

已验证前端生产构建：

```bash
cd frontend && npm run build
```

结果：

```text
✓ built in 1.58s
```

已验证当前本地服务：

```bash
curl -sS http://127.0.0.1:8080/api/status
```

结果：

```json
{"running_count":0,"binary_version":"146.0.7680.177.5","profiles_total":2}
```

已验证当前 `GET /api/profiles` 能列出 2 个 profile：

- `外网财眼`
- `狂刷`

二者状态均为 `stopped`。

已验证 `GET /` 返回 React `index.html`。`HEAD /` 返回 `405 Method Not Allowed`，这是因为 FastAPI 当前只定义 GET，不影响 WebView 正常打开页面。

### CloakBrowser 缓存和二进制路径

当前项目下已有缓存：

```text
/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache/chromium-145.0.7632.109.2/Chromium.app
```

`cloakbrowser` 包已核实支持：

- `CLOAKBROWSER_CACHE_DIR`：指定下载和查找 Chromium 的缓存目录。
- `CLOAKBROWSER_BINARY_PATH`：指定本地 Chromium 可执行文件，跳过下载。

macOS 下 `CLOAKBROWSER_BINARY_PATH` 应指向可执行文件，不是 `.app` 目录：

```text
/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache/chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium
```

`cloakbrowser` 的默认缓存目录是：

```text
~/.cloakbrowser
```

本地 APP 应显式设置：

```bash
CLOAKBROWSER_CACHE_DIR=/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache
```

这样不会默默写到 home 目录。

### Beads 和 GitNexus 状态

`bd` 已安装，当前版本：

```text
bd version 1.0.5 (Homebrew)
```

当前仓库现在可以定位 beads workspace：

```text
/Volumes/jd/projects/CloakBrowser-Manager/.beads
```

`bd ready` 当前结果：

```text
No open issues
```

GitNexus 现有索引显示落后 5 个提交。尝试刷新：

```bash
npx gitnexus analyze
```

失败原因：

```text
Cannot find package 'tree-sitter-kotlin'
```

后续 GitNexus `context` 调用也出现过：

```text
Transport closed
```

因此本次方案主要基于源码阅读和本机 smoke check，而不是依赖 GitNexus 最新索引。

## 用户确认点

### 是否还需要分别启动前后端

不需要。

本地 APP 实现后，日常只启动一个 APP。它会自动启动 FastAPI 后台并打开前端页面。Vite dev server 只在开发前端时需要。

### 是否可以使用当前路径下的缓存

可以。

默认使用当前项目目录：

```bash
DATA_DIR=/Volumes/jd/projects/CloakBrowser-Manager/data
CLOAKBROWSER_CACHE_DIR=/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache
TMPDIR=/Volumes/jd/projects/CloakBrowser-Manager/tmp
```

这样会复用当前目录下已经下载的 CloakBrowser Chromium。

也应支持一个显式设置项 `binary_path`。如果用户指定它，就设置：

```bash
CLOAKBROWSER_BINARY_PATH=<用户指定的 Chromium 可执行文件>
```

如果 `binary_path` 指向不存在的文件，启动时应直接报错：

```text
CLOAKBROWSER_BINARY_PATH set to '<path>' but file does not exist
```

不做隐藏兜底。

## 最小实施路径

### 第 1 步：新增桌面 APP 入口

新增文件：

```text
desktop_app.py
```

职责：

- 计算项目根目录。
- 读取本地 APP 设置文件。
- 设置必要环境变量。
- 找一个空闲本地端口。
- 启动 uvicorn。
- 等待 `/api/status` 可访问。
- 创建 pywebview 窗口加载 `http://127.0.0.1:<port>`。
- 关闭窗口时停止 uvicorn 进程。

推荐用子进程启动 uvicorn，而不是在同进程里起线程。原因更简单：

- import 顺序更清楚。
- 环境变量在子进程启动前固定。
- APP 退出时可以直接终止子进程。
- 后台报错可以原样输出到日志。

伪代码结构：

```python
def main():
    root = Path(__file__).resolve().parent
    settings = load_settings(root)
    env = build_env(root, settings)
    port = find_free_port()
    proc = start_backend(root, env, port)
    wait_until_ready(port)
    open_window(port)
    stop_backend(proc)
```

注意：不要在设置环境变量之前 import `backend.main`、`backend.database` 或 `backend.browser_manager`。

### 第 2 步：新增 APP 设置文件

新增文件：

```text
desktop-app-settings.json
```

默认内容：

```json
{
  "data_dir": "data",
  "cache_dir": "cloakbrowser-cache",
  "tmp_dir": "tmp",
  "binary_path": "",
  "host": "127.0.0.1"
}
```

路径规则：

- 相对路径按项目根目录解析。
- 绝对路径直接使用。
- `binary_path` 为空时不设置 `CLOAKBROWSER_BINARY_PATH`。
- `binary_path` 非空但不存在时直接失败。
- `data_dir`、`cache_dir`、`tmp_dir` 不存在时创建。

这是确定性默认值，不是隐藏兜底。

### 第 3 步：依赖增加 pywebview

在 backend 或桌面依赖中增加：

```text
pywebview
```

macOS 上通常还需要系统已有 WebKit 支持。先不引入 Electron、Tauri、Qt。

### 第 4 步：启动后台

启动命令应等价于：

```bash
DATA_DIR="$ROOT/data" \
CLOAKBROWSER_CACHE_DIR="$ROOT/cloakbrowser-cache" \
TMPDIR="$ROOT/tmp" \
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" --log-level info
```

不要使用 `--reload`。本地 APP 是生产运行形态，`--reload` 会产生额外 watcher 进程，关闭逻辑更复杂。

### 第 5 步：动态端口

不要固定 8080。

APP 启动时从系统申请空闲端口，再把 WebView 指向该端口。这样即使用户已有开发服务占用 8080，APP 仍能启动。

验收时必须覆盖端口冲突场景。

### 第 6 步：等待后台就绪

启动子进程后轮询：

```text
http://127.0.0.1:<port>/api/status
```

最多等待一个明确超时时间，例如 20 秒。

如果失败，直接显示错误：

```text
Backend did not become ready within 20s.
See log: <log_path>
```

不要自动换另一种启动方式。

### 第 7 步：日志落盘

新增目录：

```text
logs/
```

启动时将 uvicorn stdout/stderr 写入：

```text
logs/desktop-app.log
```

APP 启动失败时，错误信息必须包含这个日志路径。

### 第 8 步：退出清理

关闭 WebView 窗口时：

- 给 uvicorn 子进程发送正常终止信号。
- 等待进程退出。
- 超时后再 kill。

FastAPI lifespan 里已经有：

```python
await browser_mgr.cleanup_all()
```

所以正常关闭 uvicorn 会停止所有运行中的 CloakBrowser contexts。

### 第 9 步：修正相对 user_data_dir 风险

当前数据库里至少有一个 profile 的 `user_data_dir` 是相对路径：

```text
data/profiles/86561373-4350-4b17-8fd3-56fb710e2927
```

如果 APP 从 `.app` bundle 路径启动，当前工作目录可能不是项目根目录，这个相对路径会失效。

最小修复：

- `desktop_app.py` 启动 uvicorn 子进程时设置 `cwd=项目根目录`。

更稳的后续修复：

- 新建 profile 时 `user_data_dir` 始终写绝对路径。
- 对旧的相对 `user_data_dir` 做一次迁移，按 `DATA_DIR` 补成绝对路径。

第一版 APP 可以先通过 `cwd=项目根目录` 解决，不必立刻迁移数据库。

### 第 10 步：打包 macOS APP

第一阶段先提供源码运行命令：

```bash
.venv/bin/python desktop_app.py
```

验收通过后，再用 PyInstaller 打包：

```bash
pyinstaller --windowed --name "CloakBrowser Manager" desktop_app.py
```

打包时不要把 CloakBrowser Chromium 直接塞进 `.app`，原因：

- 体积很大。
- 当前 license 文档说明 CloakBrowser binary 可用但不适合随意再分发。
- 现有 `cloakbrowser` 包已经能从 `CLOAKBROWSER_CACHE_DIR` 查找或下载。

## 推荐文件变更清单

最小版本：

```text
desktop_app.py
desktop-app-settings.json
backend/requirements.txt
docs/local-app-implementation-plan.md
```

可选后续：

```text
scripts/build-macos-app.sh
```

暂不建议新增：

- Electron 工程。
- Tauri 工程。
- 独立桌面状态管理层。
- 新的 profile 管理 API。
- 新的数据库。

## 验收步骤

### 验收 1：前端生产构建

命令：

```bash
cd /Volumes/jd/projects/CloakBrowser-Manager/frontend
npm run build
```

通过标准：

```text
✓ built
```

并生成：

```text
frontend/dist/index.html
frontend/dist/assets/*.js
frontend/dist/assets/*.css
```

### 验收 2：后台测试

命令：

```bash
cd /Volumes/jd/projects/CloakBrowser-Manager
pytest backend/tests/
```

通过标准：

```text
所有 backend tests passed
```

说明：后台测试 mock 掉了 `cloakbrowser`，不需要真实浏览器。

### 验收 3：APP 源码启动

命令：

```bash
cd /Volumes/jd/projects/CloakBrowser-Manager
.venv/bin/python desktop_app.py
```

通过标准：

- 出现一个桌面窗口。
- 窗口内显示现有 CloakBrowser Manager UI。
- 不需要手动启动 `uvicorn`。
- 不需要手动启动 `npm run dev`。
- `ps` 中能看到一个由 APP 启动的 uvicorn 进程。
- 不应该出现 Vite 进程。

### 验收 4：API 健康检查

从日志或 APP 输出找到端口，例如 `<port>`。

命令：

```bash
curl -sS http://127.0.0.1:<port>/api/status
```

通过标准：

返回 JSON，至少包含：

```json
{
  "running_count": 0,
  "binary_version": "...",
  "profiles_total": 2
}
```

`profiles_total` 应与当前 `data/profiles.db` 中的 profile 数一致。

### 验收 5：使用当前项目数据

在 APP UI 中检查 profile 列表。

通过标准：

- 能看到当前已有 profile。
- 当前机器上应至少看到：
  - `外网财眼`
  - `狂刷`
- profile 的 tags、proxy、launch args、auto_launch 等字段能正常展示和编辑。

### 验收 6：使用当前项目缓存

启动 APP 后，检查环境和日志。

通过标准：

- 日志中不应显示写入默认 `~/.cloakbrowser`。
- `CLOAKBROWSER_CACHE_DIR` 应指向：

```text
/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache
```

启动 profile 后，CloakBrowser 应从这个 cache 查找 Chromium。

### 验收 7：启动 profile

在 APP 中选择一个 profile，点击 Launch。

通过标准：

- 打开一个本地 CloakBrowser 窗口。
- UI 中 profile 状态变为 `running`。
- `/api/profiles` 返回该 profile 的：

```json
{
  "status": "running",
  "cdp_url": "/api/profiles/<id>/cdp"
}
```

### 验收 8：停止 profile

在 APP 中点击 Stop。

通过标准：

- CloakBrowser 窗口关闭。
- UI 中 profile 状态变为 `stopped`。
- `/api/profiles/{id}/status` 返回：

```json
{
  "status": "stopped",
  "cdp_url": null
}
```

### 验收 9：CDP URL

启动一个 profile 后，复制 CDP URL。

命令：

```bash
curl -sS http://127.0.0.1:<port>/api/profiles/<id>/cdp/json/version
```

通过标准：

- 返回 Chrome CDP version JSON。
- `webSocketDebuggerUrl` 中的 host 和 port 指向 APP 当前端口。

### 验收 10：APP 退出清理

启动一个 profile 后，直接关闭 APP 窗口。

通过标准：

- uvicorn 子进程退出。
- 已启动的 CloakBrowser profile 被关闭。
- 再次启动 APP 时，profile 不应错误显示为 running。
- 不应残留占用 APP 端口的进程。

辅助命令：

```bash
ps -ax -o pid,command | rg 'uvicorn backend.main|Chromium.app|cloakbrowser'
```

### 验收 11：端口冲突

先占用 8080：

```bash
python -m http.server 8080
```

再启动 APP。

通过标准：

- APP 仍能启动。
- APP 使用另一个动态端口。
- UI 和 API 正常工作。

### 验收 12：binary_path 显式配置

在 `desktop-app-settings.json` 中设置：

```json
{
  "binary_path": "/Volumes/jd/projects/CloakBrowser-Manager/cloakbrowser-cache/chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium"
}
```

启动 APP 并 Launch profile。

通过标准：

- 使用指定二进制。
- 如果路径存在，profile 能启动。

再把 `binary_path` 改成不存在的路径。

通过标准：

- APP 或后台启动时直接失败。
- 错误信息明确包含不存在的路径。
- 不自动切换到其他 Chromium。

### 验收 13：打包后的 macOS APP

命令：

```bash
pyinstaller --windowed --name "CloakBrowser Manager" desktop_app.py
open "dist/CloakBrowser Manager.app"
```

通过标准：

- `.app` 能打开窗口。
- 不需要打开终端。
- profile 列表来自当前项目 `data/`。
- Launch / Stop 正常。
- 退出 `.app` 后后台进程关闭。

## 风险和处理

### 风险 1：`.app` 启动 cwd 不稳定

处理：

- 启动 uvicorn 子进程时显式设置 `cwd=项目根目录`。
- 后续再迁移相对 `user_data_dir`。

### 风险 2：CloakBrowser 下载或更新写到 home

处理：

- APP 启动前固定设置 `CLOAKBROWSER_CACHE_DIR`。
- 验收时检查日志和缓存目录。

### 风险 3：关闭 APP 后浏览器残留

处理：

- 优先正常终止 uvicorn，让 FastAPI lifespan 执行 `cleanup_all()`。
- 超时再 kill uvicorn。
- 不直接 `pkill` CloakBrowser，避免误杀用户手动开的其他实例。

### 风险 4：pywebview 安装或 macOS 权限问题

处理：

- 第一版先支持 `.venv/bin/python desktop_app.py`。
- 打包问题单独处理，不阻塞核心功能。

### 风险 5：GitNexus 索引当前不可靠

处理：

- 实施前可先修复 `tree-sitter-kotlin` 依赖问题，再重跑 `npx gitnexus analyze`。
- 如果只改新增桌面入口和 requirements，影响范围低；涉及 `backend/main.py` 或 `browser_manager.py` 前仍应做 impact 分析。

## 最小验收口径

本地 APP 第一版只要满足以下条件即可认为完成：

- 一个命令或一个 `.app` 能启动 UI。
- 不需要单独启动后端。
- 不需要单独启动前端。
- 读取当前项目 `data/profiles.db`。
- 使用当前项目 `cloakbrowser-cache`。
- 能 Launch profile。
- 能 Stop profile。
- 关闭 APP 后后台进程和 profile 都退出。
- 路径配置错误时直接显示可定位错误。

