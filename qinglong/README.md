# 青龙面板集成（可选）

自动识别青龙环境并把运行日志通过青龙自带通知渠道推送；非青龙环境等价于直接跑 `main.py`。

**启用**（自动）：检测到 `QL_DIR`/`QL_BRANCH` 或 `/ql` 目录即开启；
`BOHE_QL_NOTIFY=1/0` 可强制开/关。

**青龙配置**：

1. 依赖管理(Python)：`curl-cffi`
2. 环境变量 `BOHE_ACCOUNTS`：`[{"bohe_session_cookies":"你的auth_token值"}]`
3. 定时任务指向本入口（不是 main.py）：
   ```
   0 0 * * *  task <仓库名>/qinglong/runner.py
   ```
4. 通知渠道在青龙「通知设置」里配好即可，自动复用。

> 会话过期后需手动更新 `bohe_session_cookies`；想存仓库外设 `BOHE_DATA_DIR`。
