import re
import asyncio
import time
from urllib.parse import quote

import httpx
import nonebot
from nonebot import on_request
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupRequestEvent
from nonebot.adapters.onebot.v11.message import MessageSegment


__plugin_meta__ = PluginMetadata(
    name='osu!入群验证',
    type='application',
    description='osu!账户自动审批入群申请（osu! API v2）',
    homepage='https://github.com/NanamiYuk1/nonebot-plugin-osuverify',
    usage=(
        "读取入群申请中的答案，通过 osu! API v2 按用户名或 UID 校验账号：\n"
        "· 校验通过 -> 自动批准入群，并把群名片改为规范 osu! 用户名\n"
        "· 有答案但查不到账号 -> 不做任何处理，保留申请状态交由管理员手动审核\n"
        "· 未检测到答案 / 答案为空 / 机器人 API 未配置 -> 拒绝申请并提示原因"
    ),
    config={},
    supported_adapters={"~onebot.v11"},
    extra={}
)

join_group = on_request(priority=1, block=True)

# ========== Token 缓存管理 ==========
_token_cache: dict = {"access_token": None, "expires_at": 0}


async def get_osu_token() -> str | None:
    """获取并缓存 osu! API v2 的 access_token"""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    config = nonebot.get_driver().config
    client_id = getattr(config, "osu_oauth_client_id", None)
    client_secret = getattr(config, "osu_oauth_client_secret", None)

    if not client_id or not client_secret:
        nonebot.logger.error(
            "osu! API v2: OSU_OAUTH_CLIENT_ID 或 OSU_OAUTH_CLIENT_SECRET 未配置"
        )
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://osu.ppy.sh/oauth/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                    "scope": "public",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            _token_cache["access_token"] = data["access_token"]
            _token_cache["expires_at"] = now + data.get("expires_in", 86400)
            nonebot.logger.info("osu! API v2: Token 获取成功")
            return _token_cache["access_token"]
    except Exception as e:
        nonebot.logger.error(f"osu! API v2: Token 获取失败 - {e}")
        return None


# 中文常见标点 → 半角对应字符（部分不在全角 ASCII 连续区间内，需单独映射）
_CN_PUNCT_MAP = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "。": ".",
    "、": ",",
    "《": "<",
    "》": ">",
    "〈": "<",
    "〉": ">",
    "「": "[",
    "」": "]",
    "『": "[",
    "』": "]",
    "【": "[",
    "】": "]",
    "〔": "[",
    "〕": "]",
    "〖": "[",
    "〗": "]",
}


def normalize_osu_query(text: str) -> str:
    """把入群答案中的全角字符与中文标点规范化成半角，便于匹配 osu! 用户名。

    - 全角 ASCII（！-～，U+FF01-U+FF5E，含［］（）等）→ 半角
    - 全角空格（U+3000）→ 半角空格
    - 其余中文标点按 _CN_PUNCT_MAP 映射
    例：［ cz ］ → [ cz ]，４０８ → 408
    """
    normalized = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            normalized.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            normalized.append(" ")
        else:
            normalized.append(_CN_PUNCT_MAP.get(ch, ch))
    return "".join(normalized).strip()


async def check_user(query: str) -> str | None:
    """
    通过 osu! API v2 查询用户是否存在
    返回: 规范用户名(str) 或 None(不存在/出错)
    支持用户名和 UID 两种输入方式
    修复: 处理纯数字用户名的情况
    新增: 答案中的全角字符/中文标点先转半角再匹配（如 ［ cz ］ -> [ cz ]）
    """
    query = normalize_osu_query(query)
    if not query:
        return None

    token = await get_osu_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    # 辅助函数：执行单次请求
    async def fetch_user(url: str) -> str | None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("username")
                elif resp.status_code == 404:
                    return None
                else:
                    nonebot.logger.warning(
                        f"osu! API v2: 查询异常 status={resp.status_code} url={url} body={resp.text[:200]}"
                    )
                    return None
        except Exception as e:
            nonebot.logger.error(f"osu! API v2: 请求失败 url={url} - {e}")
            return None

    # 策略 1: 无论是不是数字，先尝试作为【用户名】查询
    # 使用 @ 前缀强制按用户名搜索；quote 处理用户名中的空格等特殊字符
    url_by_name = f"https://osu.ppy.sh/api/v2/users/@{quote(query, safe='')}"
    username_found = await fetch_user(url_by_name)

    if username_found:
        # 如果作为用户名找到了，直接返回
        # 注意：这里可以加一个校验，确保返回的用户名和查询词一致（忽略大小写）
        # 防止 API 的模糊匹配带来意外（虽然 v2 的 @ 通常是精确的）
        if username_found.lower() == query.lower():
            return username_found
        else:
            # 如果 API 返回了别的名字（极少见），记录日志并继续尝试 UID
            nonebot.logger.info(f"osu! API v2: 用户名模糊匹配? 输入 '{query}' 返回 '{username_found}', 尝试 UID 查询...")

    # 策略 2: 如果作为用户名没找到，且输入是纯数字，尝试作为【UID】查询
    if query.isdigit():
        url_by_id = f"https://osu.ppy.sh/api/v2/users/{quote(query, safe='')}"
        uid_found_name = await fetch_user(url_by_id)
        if uid_found_name:
            return uid_found_name

    # 两种都没找到
    return None


@join_group.handle()
async def _grh(bot: Bot, event: GroupRequestEvent):
    if event.sub_type != "add":
        return

    # 安全提取答案，防止格式不匹配导致崩溃
    match = re.search(r"答案：(.*)", event.comment or "")
    if not match:
        await event.reject(bot, reason="未检测到验证答案，请按要求填写osu!用户名或UID")
        return

    comment = match.group(1).strip()
    if not comment:
        await event.reject(bot, reason="验证答案为空，请填写您的osu!用户名或UID")
        return

    # 查询用户，返回规范用户名或 None
    osu_username = await check_user(comment)

    if osu_username is not None:
        await event.approve(bot)
        await asyncio.sleep(2)
        try:
            await bot.set_group_card(
                group_id=event.group_id,
                user_id=event.user_id,
                card=osu_username,
            )
        except Exception as e:
            nonebot.logger.warning(f"设置群名片失败: {e}")

        # 请求事件不能通过 matcher 的 finish/send 回复（OneBot 适配器对非消息事件会抛 NotImplementedError），
        # 审批通过后直接向目标群发欢迎消息
        await bot.send_group_msg(
            group_id=event.group_id,
            message=MessageSegment.at(event.user_id)
            + f"欢迎加入本群，已将您的群名片改为您的osu!用户名: {osu_username}",
        )
    else:
        # 区分“服务未配置”和“id 校验失败”
        cfg = nonebot.get_driver().config
        if not getattr(cfg, "osu_oauth_client_id", None) or not getattr(
            cfg, "osu_oauth_client_secret", None
        ):
            await event.reject(
                bot, reason="机器人 osu! API 尚未配置完成，请联系管理员处理"
            )
            return

        # 未满足 osuid 检测（用户名/UID 均查询不到对应用户）：
        # 不做任何处理 —— 既不通过也不拒绝，保留该申请的原有状态（pending），
        # 交由管理员在群申请列表中手动审核。
        nonebot.logger.info(
            "入群申请未通过 osu! id 检测，保留申请状态待人工审核: "
            f"group={event.group_id} user={event.user_id} flag={event.flag} 申请内容='{comment}'"
        )
        return
