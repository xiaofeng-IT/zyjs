#!/usr/bin/env python3
"""
多象签到脚本
功能：签到 + 领取昨日收益 + 自动提现
环境变量：
  DX：手机号#密码，多账号用 @ 隔开
  DX_WITHDRAW=0 关闭自动提现（默认开启）
  DEBUG=true 开启调试日志
  每个账号随机生成设备指纹
"""

import hashlib
import hmac
import json
import os
import random
import secrets
import sys
import time
import urllib.parse
from datetime import datetime

import requests

# ---------- 日志工具 ----------
def _log(level, msg, *args, **kwargs):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}]", msg.format(*args, **kwargs))

def info(msg, *args, **kwargs):
    _log("INFO", msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    _log("ERROR", msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    _log("WARN", msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    if os.environ.get("DEBUG", "").lower() in ("true", "1", "yes"):
        _log("DEBUG", msg, *args, **kwargs)

# ---------- 签名算法 ----------
_OBF_BYTES = [0x39, 0x28, 0x32, 0x25, 0x34, 0x3c, 0x33, 0x3a, 0x2, 0x3c, 0x33,
              0x39, 0x2f, 0x32, 0x34, 0x39, 0x2, 0x2f, 0x38, 0x2c, 0x28, 0x38,
              0x2e, 0x29, 0x2, 0x2e, 0x34, 0x3a, 0x33, 0x2, 0x2b, 0x6c]
SECRET = ''.join(chr(b ^ 0x5d) for b in _OBF_BYTES)
assert SECRET == "duoxiang_android_request_sign_v1"

def _nonce() -> str:
    return ''.join(format(secrets.randbelow(256), '02x') for _ in range(8))

def _stable_json(obj) -> str:
    def normalize(o):
        if isinstance(o, dict):
            return {k: normalize(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [normalize(x) for x in o]
        return o
    return json.dumps(normalize(obj), separators=(',', ':'), ensure_ascii=False)

def _body_hash(body) -> str:
    if body is None:
        return ""
    return hashlib.sha256(_stable_json(body).encode('utf-8')).hexdigest()

def _canonical_query(params) -> str:
    if not isinstance(params, dict) or not params:
        return ""
    items = sorted(params.items(), key=lambda kv: (kv[0], kv[1]))
    return "&".join(
        f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in items
    )

def _token(headers) -> str:
    auth = (headers or {}).get("Authorization")
    if not auth:
        return ""
    auth = auth.strip()
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""

def sign(method: str, url: str, headers: dict, body=None, params=None) -> dict:
    timestamp = str(int(time.time() * 1000))
    nonce = _nonce()
    uri = urllib.parse.urlparse(url)
    path = uri.path or "/"

    token = _token(headers)
    device_id = ((headers or {}).get("X-Device-Id") or "").strip()

    parts = [
        "android",
        timestamp,
        nonce,
        method.upper(),
        path,
        _canonical_query(params),
        _body_hash(body),
        token,
        device_id,
    ]
    signing_string = "\n".join(parts)
    mac = hmac.new(SECRET.encode('utf-8'), signing_string.encode('utf-8'), hashlib.sha256)
    x_sign = mac.hexdigest()

    debug("签名串各部分:")
    for i, p in enumerate(parts):
        debug("  [{}] {}", i, repr(p))
    debug("完整签名串:\n{}", signing_string)
    debug("计算出的 X-Sign: {}", x_sign)

    return {
        "X-Client-Type": "android",
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Sign": x_sign,
    }

# ---------- 随机设备指纹生成 ----------
def generate_random_device_headers():
    """生成随机设备信息，用于每个账号独立指纹"""
    device_id = ''.join(secrets.choice('0123456789ABCDEF') for _ in range(16))
    brands = ["XIAOMI", "HUAWEI", "OPPO", "VIVO", "SAMSUNG", "ONEPLUS", "Realme", "Meizu"]
    models = ["10X", "P40", "Reno", "X60", "Galaxy", "9", "GT", "16s"]
    resolutions = ["1080x2256", "1080x2400", "1440x2560", "1080x2340"]
    os_versions = ["9", "10", "11", "12", "13"]
    
    brand = random.choice(brands)
    model = random.choice(models)
    resolution = random.choice(resolutions)
    os_ver = random.choice(os_versions)
    
    return {
        "X-Device-Id": device_id,
        "X-Device-Name": model,
        "X-Device-Brand": brand,
        "X-Device-Manufacturer": brand,
        "X-Device-Resolution": resolution,
        "X-Device-Os-Version": os_ver,
    }

# ---------- 基础请求头 ----------
BASE_HEADERS_TEMPLATE = {
    "User-Agent": "okhttp/4.9.0",                     # 模拟安卓 APP
    "Accept-Encoding": "gzip",
    "Version": "1.8.2",
    "VersionCode": "182",
    "X-Device-Os-Name": "Android",
    "X-Device-Platform": "android",
    "Content-Type": "application/json",
}

BASE_URL = "https://dx.qqdd.top"

# ---------- 登录（直连，无代理） ----------
def login(phone: str, password: str, device_headers: dict):
    url = f"{BASE_URL}/api/user/login"
    # 加入设备信息，与 Header 中的随机指纹一致
    body = {
        "phone": phone,
        "password": password,
        "deviceId": device_headers.get("X-Device-Id"),
        "deviceModel": device_headers.get("X-Device-Name"),
        "brand": device_headers.get("X-Device-Brand"),
        "os": "Android",
    }
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    sig_headers = sign("POST", url, headers, body=body)
    headers.update(sig_headers)

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            error("登录 HTTP 错误 ({}): 状态码 {}，响应: {}", phone, resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        if data.get("status") is True:
            token = data.get("results", {}).get("token")
            if token:
                info("✅ 登录成功: {}", phone)
                return token
            else:
                error("❌ 登录响应无 token: {}", phone)
                return None
        else:
            error("❌ 登录失败: {}，消息: {}", phone, data.get("message", "未知错误"))
            return None
    except Exception as e:
        error("❌ 登录异常: {} - {}", phone, e)
        return None

# ---------- 签到 ----------
def checkin(token: str, phone: str, device_headers: dict):
    url = f"{BASE_URL}/api/growth/checkin"
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("POST", url, headers, body=None)
    headers.update(sig_headers)

    try:
        resp = requests.post(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            if resp.status_code == 400:
                try:
                    data = resp.json()
                    if data.get("message") == "今日已签到":
                        info("✅ 签到: {} - 今日已签到", phone)
                        return True
                except:
                    pass
            error("签到 HTTP 错误 ({}): 状态码 {}，响应: {}", phone, resp.status_code, resp.text[:200])
            return False
        data = resp.json()
        if data.get("status") is True:
            msg = data.get("message", "")
            results = data.get("results", {})
            points = results.get("rewardPoints", 0)
            streak = results.get("streakDays", 0)
            info("✅ 签到成功: {} - {}，今日积分 +{}，连续签到 {} 天", phone, msg, points, streak)
            return True
        else:
            if data.get("message") == "今日已签到":
                info("✅ 签到: {} - 今日已签到", phone)
                return True
            error("❌ 签到失败: {} - {}", phone, data.get("message", "未知错误"))
            return False
    except Exception as e:
        error("❌ 签到异常: {} - {}", phone, e)
        return False

# ---------- 领取收益 ----------
def invite_overview(token: str, phone: str, device_headers: dict):
    url = f"{BASE_URL}/api/invite/overview"
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("GET", url, headers, body=None)
    headers.update(sig_headers)
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            error("邀请概览 HTTP 错误 ({}): 状态码 {}，响应: {}", phone, resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        if data.get("status") is True:
            return data.get("results") or {}
        error("邀请概览失败: {} - {}", phone, data.get("message", "未知错误"))
        return None
    except Exception as e:
        error("邀请概览异常: {} - {}", phone, e)
        return None

def claim_active_reward(token: str, phone: str, offset_days: int, device_headers: dict):
    url = f"{BASE_URL}/api/invite/active-reward/claim"
    body = {"offsetDays": int(offset_days)}
    label = {1: "昨天", 2: "前天"}.get(int(offset_days), f"offsetDays={offset_days}")
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("POST", url, headers, body=body)
    headers.update(sig_headers)
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            error("领取{} HTTP 错误 ({}): 状态码 {}，响应: {}", label, phone, resp.status_code, resp.text[:200])
            return False
        data = resp.json()
        msg = data.get("message", "")
        if data.get("status") is True:
            results = data.get("results") or {}
            amount = results.get("amount")
            balance = results.get("balance")
            parts = []
            if amount is not None:
                try:
                    parts.append(f"到账 {float(amount) / 100:.2f} 元")
                except (TypeError, ValueError):
                    parts.append(f"到账 {amount}")
            if balance is not None:
                try:
                    parts.append(f"余额 {float(balance) / 100:.2f} 元")
                except (TypeError, ValueError):
                    parts.append(f"余额 {balance}")
            extra = ("，" + "，".join(parts)) if parts else ""
            info("✅ 领取{}成功: {} - {}{}", label, phone, msg, extra)
            return True
        if "已领取" in msg or "已领过" in msg:
            info("ℹ️ 领取{}: {} - {}", label, phone, msg)
            return True
        warning("领取{}: {} - {}", label, phone, msg)
        return False
    except Exception as e:
        error("领取{}异常: {} - {}", label, phone, e)
        return False

def claim_yesterday_income(token: str, phone: str, device_headers: dict):
    overview = invite_overview(token, phone, device_headers)
    if overview is None:
        return False

    stats = overview.get("stats") or []
    targets = [s for s in stats if s.get("canClaim") is True]
    if not targets:
        targets = [
            s
            for s in stats
            if int(s.get("offsetDays") or -1) in (1, 2)
            and s.get("rewardPaid") is not True
            and float(s.get("totalRewardAmount") or 0) > 0
        ]

    if not targets:
        yest = next((s for s in stats if int(s.get("offsetDays") or -1) == 1), None)
        if yest is not None:
            paid = yest.get("rewardPaid")
            reward = yest.get("reward")
            if paid is True:
                info("领取收益: {} - 昨天奖励已领取（金额 {} 元）", phone, reward)
            else:
                info("领取收益: {} - 昨天暂无可领（奖励 {}）", phone, reward)
        else:
            info("领取收益: {} - 暂无可领取的活跃奖", phone)
        return False

    ok_any = False
    for s in sorted(targets, key=lambda x: int(x.get("offsetDays") or 99)):
        od = int(s.get("offsetDays") or 0)
        if od not in (1, 2):
            continue
        label = s.get("label") or ({1: "昨天", 2: "前天"}.get(od, str(od)))
        reward = s.get("reward")
        info("领取收益: {} - 准备领取{}（奖励 {}）...", phone, label, reward)
        if claim_active_reward(token, phone, od, device_headers):
            ok_any = True
        time.sleep(random.uniform(1.0, 2.5))
    return ok_any

# ---------- 提现 ----------
def get_profile(token: str, phone: str, device_headers: dict):
    url = f"{BASE_URL}/api/user/profile"
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("GET", url, headers, body=None)
    headers.update(sig_headers)
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            error("资料 HTTP 错误 ({}): 状态码 {}，响应: {}", phone, resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        if data.get("status") is True:
            return data.get("results") or {}
        error("资料失败: {} - {}", phone, data.get("message", "未知错误"))
        return None
    except Exception as e:
        error("资料异常: {} - {}", phone, e)
        return None

def withdraw_balance(token: str, phone: str, amount_fen: int, device_headers: dict):
    url = f"{BASE_URL}/api/balance/withdraw"
    body = {"amount": int(amount_fen)}
    yuan = int(amount_fen) / 100
    headers = BASE_HEADERS_TEMPLATE.copy()
    headers.update(device_headers)
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("POST", url, headers, body=body)
    headers.update(sig_headers)
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            error("提现 HTTP 错误 ({}): 状态码 {}，响应: {}", phone, resp.status_code, resp.text[:200])
            return False
        data = resp.json()
        msg = data.get("message", "")
        if data.get("status") is True:
            results = data.get("results") or {}
            wno = results.get("withdrawNo") or results.get("orderNo") or ""
            extra = f"，单号 {wno}" if wno else ""
            info("✅ 提现成功: {} - {}，提现 {:.2f} 元{}", phone, msg, yuan, extra)
            return True
        warning("提现失败: {} - {}", phone, msg)
        return False
    except Exception as e:
        error("提现异常: {} - {}", phone, e)
        return False

def auto_withdraw(token: str, phone: str, device_headers: dict):
    if os.environ.get("DX_WITHDRAW", "1").lower() in ("0", "false", "no", "off"):
        info("💤 提现: {} - 已关闭（DX_WITHDRAW=0）", phone)
        return False

    profile = get_profile(token, phone, device_headers)
    if profile is None:
        warning("提现: {} - 获取用户资料失败，无法提现", phone)
        return False

    try:
        balance = int(profile.get("balance") or 0)
    except (TypeError, ValueError):
        balance = 0

    alipay = (profile.get("alipayAccount") or "").strip()
    real_name = (profile.get("personalVerifiedName") or profile.get("realName") or "").strip()
    unit = 100
    min_amount = 100
    withdraw_amount = (balance // unit) * unit

    info("💰 提现信息: {} - 余额 {:.2f} 元，整元可提 {:.2f} 元，支付宝={}，实名={}",
         phone, balance / 100, withdraw_amount / 100,
         alipay if alipay else "未绑定",
         real_name if real_name else "未认证")

    if not alipay:
        warning("❌ 提现: {} - 未绑定支付宝，跳过", phone)
        return False
    if not real_name:
        warning("❌ 提现: {} - 未实名认证，跳过", phone)
        return False
    if withdraw_amount < min_amount:
        if balance % 100 > 0:
            info("⏭️ 提现: {} - 余额 {:.2f} 元不足整元（零头 {} 分），保留零头", phone, balance/100, balance % 100)
        else:
            info("⏭️ 提现: {} - 余额为 0，无需提现", phone)
        return False

    info("📤 提现: {} - 发起提现 {:.2f} 元...", phone, withdraw_amount / 100)
    success = withdraw_balance(token, phone, withdraw_amount, device_headers)
    if success:
        info("✅ 提现: {} - 提现成功，金额 {:.2f} 元已提交", phone, withdraw_amount / 100)
    else:
        error("❌ 提现: {} - 提现失败，请检查账户状态或网络", phone)
    return success

# ---------- 主函数 ----------
def main():
    dx_env = os.environ.get("DX", "")
    if not dx_env:
        error("❌ 未设置环境变量 DX，请设置手机号#密码，多账号用 @ 隔开")
        sys.exit(1)

    accounts = []
    for item in dx_env.split("@"):
        item = item.strip()
        if not item:
            continue
        if "#" not in item:
            warning("账号格式错误（缺少 #），跳过: {}", item)
            continue
        phone, pwd = item.split("#", 1)
        accounts.append((phone.strip(), pwd.strip()))

    if not accounts:
        error("❌ 没有有效的账号，退出")
        sys.exit(1)

    info("共 {} 个账号待处理（直连，无代理）", len(accounts))
    withdraw_status = os.environ.get("DX_WITHDRAW", "1").lower() not in ("0", "false", "no", "off")
    info("自动提现: {}", "开" if withdraw_status else "关")

    for idx, (phone, pwd) in enumerate(accounts, 1):
        info("===== 处理第 {}/{} 个账号: {} =====", idx, len(accounts), phone)

        device_headers = generate_random_device_headers()
        info("设备指纹: DeviceId={}, Brand={}, Model={}",
             device_headers["X-Device-Id"], device_headers["X-Device-Brand"], device_headers["X-Device-Name"])

        token = login(phone, pwd, device_headers)
        if not token:
            error("❌ 账号 {} 登录失败，跳过", phone)
            if idx < len(accounts):
                time.sleep(random.uniform(30, 60))
            continue

        time.sleep(random.uniform(5, 10))
        checkin(token, phone, device_headers)

        time.sleep(random.uniform(2, 5))
        claim_yesterday_income(token, phone, device_headers)

        time.sleep(random.uniform(2, 4))
        auto_withdraw(token, phone, device_headers)

        if idx < len(accounts):
            time.sleep(random.uniform(30, 60))

    info("所有账号处理完毕！")

if __name__ == "__main__":
    main()