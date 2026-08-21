"""
JLC 嘉立创小程序签到脚本
支持：青龙面板 / 多账号 / 消息推送 / 豆豆查询

改编：添加运行日志记录功能

使用说明：
【抓包获取参数】
1. 使用抓包工具（如 Stream、HttpCanary）
2. 打开嘉立创小程序，进入签到页面
3. 抓取域名 https://m.jlc.com/api/sms/front/internal-message/unread-count 的请求
4. 在请求头中找到以下两个值：
   - x-jlc-accesstoken  → 这是 token
   - secretkey          → 这是 secret
【环境变量配置】
方式一（推荐）：JLC_AUTH
格式：token#secret
多账号用 & 或换行分隔
示例（单账号）：
JLC_AUTH=abc123token#xyz789secret
示例（多账号）：
JLC_AUTH=token1#secret1&token2#secret2
"""
import os
import sys
import json
import time
import random
import traceback
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging
import requests
import base64

_ENCODED_SOURCE = "5p2l5rqQ5YWs5LyX5Y+377ya6JGj5bCP5Z2b"

def get_source_info() -> str:
    """解码来源信息"""
    try:
        return base64.b64decode(_ENCODED_SOURCE).decode('utf-8')
    except:
        return "未知来源"

# ============ 日志配置 ============
def setup_logger() -> logging.Logger:
    """配置日志记录器"""
    # 创建logger
    logger = logging.getLogger("JLC_SIGN")
    logger.setLevel(logging.DEBUG)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler - 按日期命名
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"jlc_sign_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 初始化日志
logger = setup_logger()

# ============ 配置区 ============
BASE_URL = "https://m.jlc.com"
PLATFORM_TYPE = "MP-WEIXIN"
SOURCE = "2"

# ============ 工具函数 ============
def get_env(key: str, default: str = "") -> str:
    """获取环境变量"""
    return os.environ.get(key, "").strip() or default

def split_accounts(text: str) -> List[str]:
    """分割多账号字符串，支持 & 或换行"""
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    result = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for part in line.split("&"):
            part = part.strip()
            if part:
                result.append(part)
    return result

def parse_accounts() -> List[Dict[str, str]]:
    """解析账号配置"""
    logger.info("开始解析账号配置...")
    auth_raw = get_env("JLC_AUTH")
    remarks_raw = get_env("JLC_REMARKS")
    remarks = split_accounts(remarks_raw)
    accounts = []

    if auth_raw:
        items = split_accounts(auth_raw)
        logger.debug(f"检测到 JLC_AUTH 环境变量，共 {len(items)} 个账号")
        for idx, item in enumerate(items):
            # 支持 # | , 作为分隔符
            for sep in ["#", "|", ","]:
                if sep in item:
                    token, secret = item.split(sep, 1)
                    token, secret = token.strip(), secret.strip()
                    if token and secret:
                        accounts.append({
                            "token": token,
                            "secret": secret,
                            "remark": remarks[idx] if idx < len(remarks) else f"账号{idx+1}",
                        })
                        logger.debug(f"账号 {idx+1}: {remarks[idx] if idx < len(remarks) else f'账号{idx+1}'} 解析成功")
                    break
            else:
                error_msg = f"JLC_AUTH 格式错误，第{idx+1}个账号应为 token#secret"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        return accounts

    # 兼容旧环境变量
    tokens = split_accounts(get_env("JLC_ACCESS_TOKEN"))
    secrets = split_accounts(get_env("JLC_SECRET_KEY"))
    if not tokens or not secrets:
        error_msg = "请设置环境变量 JLC_AUTH 或 JLC_ACCESS_TOKEN + JLC_SECRET_KEY"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if len(tokens) != len(secrets):
        error_msg = f"token数量({len(tokens)})与secret数量({len(secrets)})不一致"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    for idx, (t, s) in enumerate(zip(tokens, secrets)):
        accounts.append({
            "token": t,
            "secret": s,
            "remark": remarks[idx] if idx < len(remarks) else f"账号{idx+1}",
        })

    logger.info(f"账号解析完成，共 {len(accounts)} 个账号")
    return accounts

def build_headers(token: str, secret: str) -> Dict[str, str]:
    """构建请求头"""
    return {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "x-jlc-accesstoken": token,
        "secretkey": secret,
        "origin": BASE_URL,
        "referer": f"{BASE_URL}/",
        "user-agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    }

def api_request(session: requests.Session, path: str, params: Dict = None, retries: int = 3) -> Dict[str, Any]:
    """发送API请求，带重试"""
    url = BASE_URL + path
    for attempt in range(retries):
        try:
            logger.debug(f"API请求: {url}, 参数: {params}, 尝试: {attempt+1}/{retries}")
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            logger.debug(f"API响应: {url}, 成功: {result.get('success')}, 消息: {result.get('msg', '')}")
            return result
        except Exception as e:
            logger.warning(f"请求失败 (尝试 {attempt+1}/{retries}): {url} - {str(e)}")
            if attempt == retries - 1:
                error_msg = f"请求失败({retries}次): {url} - {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            time.sleep(random.randint(2, 5))
    return {}

def send_notify(title: str, content: str) -> None:
    """发送通知（青龙面板）"""
    try:
        from notify import send
        logger.info(f"发送通知: {title}")
        send(title, content)
    except Exception as e:
        logger.warning(f"推送跳过：未配置notify或推送失败 - {str(e)}")
        print("（推送跳过：未配置notify或推送失败）")

# ============ 核心逻辑 ============
def check_sign_status(session: requests.Session) -> Dict[str, Any]:
    """查询签到状态"""
    return api_request(session, "/api/activity/sign/getCurrentUserSignInConfig", {"platformType": PLATFORM_TYPE})

def do_sign_in(session: requests.Session) -> Dict[str, Any]:
    """执行签到"""
    return api_request(session, "/api/activity/sign/signIn", {"platformType": PLATFORM_TYPE, "source": SOURCE})

def get_doudou_balance(session: requests.Session) -> Dict[str, Any]:
    """查询豆豆余额"""
    return api_request(session, "/api/activity/front/getCustomerIntegral")

def process_account(remark: str, token: str, secret: str) -> Tuple[bool, str, int]:
    """
    处理单个账号
    返回: (是否成功, 日志信息, 豆豆总数)
    """
    logs = []
    success = True
    total_doudou = 0

    logger.info(f"开始处理账号: {remark}")
    with requests.Session() as session:
        session.headers.update(build_headers(token, secret))

        # 1. 查询签到状态
        try:
            logger.debug(f"[{remark}] 查询签到状态...")
            status = check_sign_status(session)
            if not status.get("success"):
                error_msg = f"查询状态失败: {status.get('msg', '未知错误')}"
                logs.append(f"❌ [{remark}] {error_msg}")
                logger.error(f"[{remark}] {error_msg}")
                return False, "\n".join(logs), 0
            already_signed = status.get("data", {}).get("haveSignIn", False)
            logger.debug(f"[{remark}] 签到状态: {'已签到' if already_signed else '未签到'}")
        except Exception as e:
            error_msg = f"查询状态异常: {str(e)}"
            logs.append(f"❌ [{remark}] {error_msg}")
            logger.error(f"[{remark}] {error_msg}")
            logger.error(traceback.format_exc())
            return False, "\n".join(logs), 0

        # 2. 执行签到
        if already_signed:
            logs.append(f"✅ [{remark}] 今日已签到，无需重复")
            logger.info(f"[{remark}] 今日已签到，无需重复")
        else:
            try:
                logger.debug(f"[{remark}] 执行签到...")
                result = do_sign_in(session)
                if result.get("success"):
                    gain = result.get("data", {}).get("gainNum", 0)
                    logs.append(f"✅ [{remark}] 签到成功！获得 {gain} 豆豆")
                    logger.info(f"[{remark}] 签到成功！获得 {gain} 豆豆")
                else:
                    error_msg = f"签到失败: {result.get('msg', '未知错误')}"
                    logs.append(f"❌ [{remark}] {error_msg}")
                    logger.error(f"[{remark}] {error_msg}")
                    success = False
            except Exception as e:
                error_msg = f"签到异常: {str(e)}"
                logs.append(f"❌ [{remark}] {error_msg}")
                logger.error(f"[{remark}] {error_msg}")
                logger.error(traceback.format_exc())
                success = False

        # 3. 查询豆豆余额
        try:
            logger.debug(f"[{remark}] 查询豆豆余额...")
            balance = get_doudou_balance(session)
            if balance.get("success"):
                data = balance.get("data", {})
                total_doudou = data.get("integralVoucher", 0)
                expire = data.get("expireTime", "")
                expire_info = f"（{expire}到期）" if expire else ""
                logs.append(f"💰 [{remark}] 豆豆余额: {total_doudou}{expire_info}")
                logger.info(f"[{remark}] 豆豆余额: {total_doudou}{expire_info}")
            else:
                logs.append(f"⚠️ [{remark}] 查询余额失败")
                logger.warning(f"[{remark}] 查询余额失败")
        except Exception as e:
            logs.append(f"⚠️ [{remark}] 查询余额异常: {str(e)}")
            logger.error(f"[{remark}] 查询余额异常: {str(e)}")

    logger.info(f"账号处理完成: {remark}, 结果: {'成功' if success else '失败'}")
    return success, "\n".join(logs), total_doudou

def main() -> int:
    """主函数"""
    source_info = get_source_info()
    
    print("=" * 50)
    print("🐱 JLC 嘉立创签到脚本启动喵~")
    print(f"📢 {source_info}")
    print("=" * 50)

    # 解析账号
    try:
        accounts = parse_accounts()
    except Exception as e:
        error_msg = f"账号解析失败: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        send_notify("JLC签到失败", f"账号解析失败: {str(e)}")
        return 1

    print(f"📋 共 {len(accounts)} 个账号")
    print("-" * 50)
    logger.info(f"共 {len(accounts)} 个账号待处理")

    all_logs = []
    push_msgs = []
    has_error = False

    for idx, acc in enumerate(accounts):
        # 多账号间随机延迟
        if idx > 0:
            delay = random.randint(5, 15)
            print(f"⏳ 等待 {delay} 秒...")
            logger.info(f"账号间延迟 {delay} 秒")
            time.sleep(delay)

        remark = acc["remark"]
        logger.info(f"开始处理第 {idx+1}/{len(accounts)} 个账号: {remark}")
        success, log_text, doudou = process_account(remark, acc["token"], acc["secret"])

        print(log_text)
        print("-" * 50)
        all_logs.append(log_text)

        if success:
            push_msgs.append(f"✅ {remark}: 豆豆 {doudou}")
        else:
            push_msgs.append(f"❌ {remark}: 失败")
            has_error = True

    # 发送通知
    title = "JLC签到结果"
    content = "\n".join(push_msgs)
    send_notify(title, content)

    # 输出汇总
    print("=" * 50)
    print("🐱 全部执行完毕喵~")
    print(f"📊 处理结果: {'全部成功' if not has_error else '存在失败'}")
    print("=" * 50)

    return 1 if has_error else 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        error_msg = f"脚本异常: {str(e)}"
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        send_notify("JLC签到异常", str(e))
        sys.exit(1)
