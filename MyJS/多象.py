#!/usr/bin/env python3
"""
多象 (duoxiang) 青龙面板签到脚本
环境变量 DX：手机号#密码，多账号用 @ 隔开
"""

import hashlib
import hmac
import json
import os
import random
import secrets
import time
import urllib.parse
import sys
import requests

# ---------- 签名算法 ----------
_OBF_BYTES = [0x39, 0x28, 0x32, 0x25, 0x34, 0x3c, 0x33, 0x3a, 0x2, 0x3c, 0x33,
              0x39, 0x2f, 0x32, 0x34, 0x39, 0x2, 0x2f, 0x38, 0x2c, 0x28, 0x38,
              0x2e, 0x29, 0x2, 0x2e, 0x34, 0x3a, 0x33, 0x2, 0x2b, 0x6c]
SECRET = ''.join(chr(b ^ 0x5d) for b in _OBF_BYTES)
assert SECRET == "duoxiang_android_request_sign_v1"

def _nonce() -> str:
    return ''.join(format(secrets.randbelow(256), '02x') for _ in range(8))

def _stable_json(obj) -> str:
    """稳定JSON：递归按键排序后序列化，使用紧凑格式（无空格）"""
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

DEBUG = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")

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

    if DEBUG:
        print(f"=== 调试信息 ===")
        print(f"签名串各部分 (用换行连接):")
        for i, p in enumerate(parts):
            print(f"  [{i}] {repr(p)}")
        print(f"完整签名串:\n{signing_string}")
        print(f"计算出的 X-Sign: {x_sign}")
        print(f"================")

    return {
        "X-Client-Type": "android",
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Sign": x_sign,
    }

# ---------- 业务逻辑 ----------
BASE_URL = "https://dx.qqdd.top"
DEVICE_ID = "25C1D83B333A1393"

COMMON_HEADERS = {
    "User-Agent": "Dart/3.11 (dart:io)",
    "Accept-Encoding": "gzip",
    "Version": "1.8.2",
    "VersionCode": "182",
    "X-Device-Os-Version": "9",
    "X-Device-Resolution": "1080x2256",
    "X-Device-Os-Name": "Android",
    "X-Device-Name": "10X",
    "X-Device-Platform": "android",
    "X-Device-Brand": "XIAOMI",
    "X-Device-Manufacturer": "XIAOMI",
    "X-Device-Id": DEVICE_ID,
    "Content-Type": "application/json",
}

def login(phone: str, password: str):
    url = f"{BASE_URL}/api/user/login"
    body = {"phone": phone, "password": password}
    headers = COMMON_HEADERS.copy()
    sig_headers = sign("POST", url, headers, body=body)
    headers.update(sig_headers)

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[登录HTTP错误] {phone}，状态码: {resp.status_code}, 响应: {resp.text[:200]}")
            return None
        data = resp.json()
        if data.get("status") is True:
            token = data.get("results", {}).get("token")
            if token:
                print(f"[登录成功] {phone}")
                return token
            else:
                print(f"[登录失败] {phone}，响应中无 token: {data}")
        else:
            print(f"[登录失败] {phone}，msg: {data.get('message')}")
        return None
    except Exception as e:
        print(f"[登录异常] {phone}: {e}")
        return None

def checkin(token: str, phone: str):
    url = f"{BASE_URL}/api/growth/checkin"
    headers = COMMON_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"
    sig_headers = sign("POST", url, headers, body=None)
    headers.update(sig_headers)

    try:
        resp = requests.post(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[签到HTTP错误] {phone}，状态码: {resp.status_code}, 响应: {resp.text[:200]}")
            return False
        data = resp.json()
        if data.get("status") is True:
            msg = data.get("message", "")
            results = data.get("results", {})
            points = results.get("rewardPoints", 0)
            streak = results.get("streakDays", 0)
            print(f"[签到成功] {phone}: {msg}，今日获得 {points} 积分，连续签到 {streak} 天")
            return True
        else:
            print(f"[签到失败] {phone}: {data.get('message')}")
            return False
    except Exception as e:
        print(f"[签到异常] {phone}: {e}")
        return False

def main():
    dx_env = os.environ.get("DX", "")
    if not dx_env:
        print("错误：未设置环境变量 DX，请设置手机号#密码，多账号用 @ 隔开")
        sys.exit(1)

    accounts = []
    for item in dx_env.split("@"):
        item = item.strip()
        if not item:
            continue
        if "#" not in item:
            print(f"警告：账号格式错误（缺少 #），跳过: {item}")
            continue
        phone, pwd = item.split("#", 1)
        accounts.append((phone.strip(), pwd.strip()))

    if not accounts:
        print("没有有效的账号，退出")
        sys.exit(1)

    print(f"共 {len(accounts)} 个账号待处理")

    for idx, (phone, pwd) in enumerate(accounts, 1):
        print(f"\n===== 处理第 {idx}/{len(accounts)} 个账号: {phone} =====")

        token = login(phone, pwd)
        if not token:
            time.sleep(random.uniform(2, 5))
            continue

        delay_login = random.uniform(5, 10)
        print(f"登录成功，等待 {delay_login:.1f} 秒后签到...")
        time.sleep(delay_login)

        checkin(token, phone)

        if idx < len(accounts):
            delay_next = random.uniform(30, 60)
            print(f"等待 {delay_next:.1f} 秒后处理下一个账号...")
            time.sleep(delay_next)

    print("\n所有账号处理完毕！")

if __name__ == "__main__":
    main()