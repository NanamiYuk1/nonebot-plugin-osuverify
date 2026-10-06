<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-osuverify

_✨ NoneBot osu! 用户审核入群（osu! API v2 版） ✨_

<a href="./LICENSE"><img src="https://img.shields.io/github/license/NanamiYuk1/nonebot-plugin-osuverify.svg" alt="license"></a>
<img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="python">
<img src="https://img.shields.io/badge/adapter-onebot%20v11-blue.svg" alt="onebot v11">
<img src="https://img.shields.io/badge/osu!-API%20v2-ff66aa.svg" alt="osu api v2">

</div>

---

## 📖 介绍

入群申请自动审核插件：读取申请人填写的**答案**，用 **osu! API v2** 校验 `用户名 / UID` 是否真实存在。

- ✅ 校验通过 → **自动批准入群** → 2 秒后把群名片改成**规范 osu! 用户名** → 群里发送欢迎消息
- 🕓 有答案但查不到账号 → **不做任何处理**，申请保持 pending，交由管理员手动审核
- ❌ 未检测到答案 / 答案为空 / 机器人 API 未配置 → 拒绝申请并给出提示原因

## 🔧 维护状态

本仓库是 [mas-alone/nonebot-plugin-osuverify](https://github.com/mas-alone/nonebot-plugin-osuverify) 的 **fork 与持续维护版本**。

- 上游基于早已停用的 **osu! API v1**（`osu_amd` API Key），最后一次提交停留在 **2024-04-23（v0.1.2）**
- 本 fork 已迁移到 **osu! API v2**，并修复了旧版若干崩溃与流程问题，详见 [与旧版的差异](#-与旧版的差异)
- Issue / PR 请提到本仓库；上游的 PyPI 包（`nonebot-plugin-osuverify`）仍是旧版 API v1，**不要**用它替代本仓库代码

## ✨ 特性

| 能力 | 说明 |
|:---|:---|
| osu! API v2 | OAuth2 `client_credentials` 模式，`access_token` 进程内缓存（默认 86400s），过期前 60s 自动刷新 |
| 用户名 + UID | 先用 `@用户名` 精确查询，失败且输入为纯数字时再按 UID 查询；返回**规范用户名**用于改名 |
| 全角容错 | 申请答案里的全角字符（`［ｃｚ］`、`４０８`）与中文标点自动转半角后再匹配 |
| 不误杀 | 查不到账号时**不再拒绝**，保留申请状态给管理员，避免误伤改名 / 大小写 / 谐音填写的玩家 |
| 健壮性 | 无「答案：」不会崩（旧版会 `IndexError`）、审批后改用 `bot.send_group_msg` 发欢迎语（旧版 `finish()` 会在请求事件上抛 `NotImplementedError`）、改名片失败只告警不中断 |
| 可观测 | 关键分支写日志：Token 获取、模糊匹配、保留待审的申请（含群号 / QQ / flag / 申请内容） |

## 💿 安装

本仓库的仓库根目录**就是插件包目录**（`__init__.py` 即插件入口），直接把整个目录放进 NoneBot 项目的插件目录即可运行。

> 本 fork 不再发布 PyPI 包（重构后上游的 `setup.py` 与 pypi 发布 workflow 已移除），因此不支持 `pip install nonebot-plugin-osuverify` / `nb plugin install`，请使用下面的方式安装。

<details>
<summary>方式一：git clone 到插件目录（推荐）</summary>

```bash
# 在 NoneBot 项目根目录下执行
git clone https://github.com/NanamiYuk1/nonebot-plugin-osuverify.git plugins/nonebot_plugin_osuverify
```

更新时：

```bash
git -C plugins/nonebot_plugin_osuverify pull
```

</details>

<details>
<summary>方式二：手动复制</summary>

把 `__init__.py` 放到 `plugins/nonebot_plugin_osuverify/__init__.py`（**目录名必须是 `nonebot_plugin_osuverify`**）。

</details>

<details>
<summary>方式三：作为子模块（多机部署）</summary>

```bash
git submodule add https://github.com/NanamiYuk1/nonebot-plugin-osuverify.git plugins/nonebot_plugin_osuverify
```

</details>

**依赖**

```bash
pip install nonebot2 nonebot-adapter-onebot httpx
```

- Python **3.10+**（代码使用了 `str | None` 类型标注）
- NoneBot2 **2.x** + OneBot v11 适配器（NapCat / Lagrange / go-cqhttp 等）

**启用插件**：在项目 `pyproject.toml` 的 `[tool.nonebot]` 中追加

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_osuverify"]
```

如果插件目录是在 `.env` 里通过 `PLUGINS` 配置的，把 `nonebot_plugin_osuverify` 加进去即可。

## ⚙️ 配置

在 NoneBot 项目的 `.env` 中填写 osu! API v2 的 OAuth 应用凭据：

| 配置项 | 必填 | 默认值 | 说明 |
|:---:|:---:|:---:|:---|
| `OSU_OAUTH_CLIENT_ID` | 是 | 无 | osu! OAuth 应用的 Client ID |
| `OSU_OAUTH_CLIENT_SECRET` | 是 | 无 | osu! OAuth 应用的 Client Secret |

```dotenv
# .env
OSU_OAUTH_CLIENT_ID=12345
OSU_OAUTH_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**如何申请**：

1. 登录 osu! 官网 → 右上角头像 → **Account settings** → **OAuth** → **New OAuth Application**
2. 名称随意（如 `qq-group-verify`），**Callback URL 填 `http://localhost`** 即可（本插件只用 `client_credentials`，不涉及回调）
3. 保存后即可看到 **Client ID** 与 **Client Secret**，填入 `.env` 后重启机器人

> Client Secret 属于敏感信息，请勿提交到公开仓库；本仓库的 `.gitignore` 已默认忽略 `.env*`。

## 🎉 使用

1. 把机器人设为群管理员
2. 群设置 → **管理群** → **加群方式** → **需要身份认证** → 选择 **需要回答问题并由管理员审核**
3. 问题示例：`请填写你的 osu! 用户名或 UID（用于验证玩家身份）`
4. 申请人回答后，腾讯会把答案以 `答案：xxx` 的形式放进申请信息（OneBot `comment` 字段），机器人据此校验

**示例**

- 申请人答 `答案：peppy` → 查到规范用户名 `peppy` → 自动通过，群名片改为 `peppy`，群内欢迎
- 申请人答 `答案：［ 408 ］` → 全角括号自动转半角 → 按 UID `408` 查到 `peppy` → 自动通过
- 申请人答 `答案：我没有osu账号` → 查不到 → **保留申请**，不通过也不拒绝，等待管理员处理
- 注：申请人实际不需要填写`答案：`字段

## 🔍 审核行为一览

| 场景 | 机器人行为 | 申请状态 |
|:---|:---|:---|
| 答案可查到 osu! 用户（用户名或 UID） | 自动批准 → 改群名片 → 群内欢迎消息 | 已同意 ✅ |
| 答案有内容但查不到 osu! 用户 | 只记录日志，**不做任何处理** | 保持待审核 🕓 |
| 申请信息里没有 `答案：` 字段 | 拒绝：`未检测到验证答案，请按要求填写osu!用户名或UID` | 已拒绝 ❌ |
| 答案为空 | 拒绝：`验证答案为空，请填写您的osu!用户名或UID` | 已拒绝 ❌ |
| 机器人未配置 API 凭据 | 拒绝：`机器人 osu! API 尚未配置完成，请联系管理员处理` | 已拒绝 ❌ |
| 事件子类型为 `invite`（邀请入群而非申请） | 不处理 | 维持原状 |
| 通过审批但改群名片失败 | 记录 `设置群名片失败` 告警，流程继续 | 已同意 ✅ |

## 🧩 常见问题

**Q：为什么有的申请一直停在「待审核」，机器人既不同意也不拒绝？**
A：这是有意设计。只有「填了答案但查不到 osu! 账号」时才会保留待审，由管理员人工判断（例如玩家填了昵称、大小写异常或 API 查询异常）。日志里会输出一条 `入群申请未通过 osu! id 检测，保留申请状态待人工审核`，包含群号、QQ、`flag` 与申请内容，方便定位。

**Q：Token 获取失败会怎样？**
A：Token 获取失败/网络异常时查询结果同样为「查不到」，因此申请会保留待审（不会误拒），同时日志输出 `osu! API v2: Token 获取失败` 或 `查询异常 status=...`，排查完凭据或网络后手动处理即可。

**Q：纯数字的 osu! 用户名会被当成 UID 吗？**
A：不会误判。插件先按**用户名**查询（`@数字`），用户名命中且与输入一致时直接通过；只有用户名查不到时才回退按 UID 查询。

**Q：群名片为什么要等 2 秒？**
A：入群申请被同意后成员数据可能尚未同步，等待 2 秒再调用 `set_group_card` 更稳；失败也只是告警。

**Q：支持其它适配器吗？**
A：目前只支持 OneBot v11（`GroupRequestEvent` 的 `set_group_add_request`）。

## 🛠 日志速查

| 日志 | 含义 |
|:---|:---|
| `osu! API v2: Token 获取成功` | 凭据有效，token 已缓存 |
| `osu! API v2: Token 获取失败 - ...` | 凭据错误 / 网络异常 |
| `osu! API v2: 查询异常 status=...` | 非 200/404 的异常响应 |
| `osu! API v2: 用户名模糊匹配? ...` | API 返回的名字与输入不一致，已回退尝试 UID |
| `入群申请未通过 osu! id 检测，保留申请状态待人工审核: ...` | 申请被保留，未做任何处理 |
| `设置群名片失败: ...` | 审批已通过但改名失败（通常是权限不足） |

## 🔄 与旧版的差异

| 项目 | 旧版（API v1） | 本版本（API v2） |
|:---|:---|:---|
| 接口 | `osu.ppy.sh/api/get_user?k=...`（v1，已弃用） | `osu.ppy.sh/api/v2/users/...` + OAuth2 |
| 配置项 | `osu_amd`（v1 API Key） | `OSU_OAUTH_CLIENT_ID` / `OSU_OAUTH_CLIENT_SECRET` |
| 查询方式 | 仅用户名 | 用户名 + UID（自动回退） |
| 全角 / 中文标点 | 不支持，需用户手打半角 | 自动规范化 |
| 无「答案：」字段 | `re.findall(...)[0]` 抛 `IndexError` | 捕获并友好拒绝 |
| 审批后的欢迎消息 | `join_group.finish(...)`，在请求事件上抛 `NotImplementedError` | `bot.send_group_msg(...)` 直接发群消息 |
| 查不到账号 | 拒绝并提示 | **保留申请状态，不做处理** |
| 异常处理 | 无 | Token 缓存、超时、非 200 响应、改名片失败均降级处理 |

## 📄 许可证

[AGPL-3.0](./LICENSE)

本项目基于 [mas-alone/nonebot-plugin-osuverify](https://github.com/mas-alone/nonebot-plugin-osuverify) 二次开发，沿用它原有的 **AGPL-3.0** 许可证发布。由于 AGPL 具有网络服务条款：如果你修改本插件并以网络服务（例如对外提供机器人）的形式供他人使用，需要向使用者提供对应的完整源码。感谢原作者的启发与 [nonebot_plugin_bf1_groptools](https://github.com/) 的灵感。
