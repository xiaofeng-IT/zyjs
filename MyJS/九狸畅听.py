#!/usr/bin/env python3
"""
九黎 App - 阅读时长上报 + 任务领取 + 提现 (多账号多线程版)
环境变量 SIGN_CONFIG: 每行一个账号，字段用 # 拼接：
usr#kt#p28#zyeid#encrypted_usr#p16#p35#p7#p1#p34#备注
"""

import gzip
import json
import os
import sys
import base64
import time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from urllib.parse import urlencode
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 账号配置 ====================
ENV_CONFIG_NAME = "SIGN_CONFIG"
CONFIG_FIELDS = ("usr", "kt", "p28", "zyeid", "encrypted_usr", "p16", "p35", "p7", "p1", "p34", "remark")


def load_accounts():
    raw = os.environ.get(ENV_CONFIG_NAME, "").strip()
    if not raw:
        print(f"未检测到环境变量 {ENV_CONFIG_NAME}")
        print(f"格式: {'#'.join(CONFIG_FIELDS)}")
        sys.exit(1)
    accounts = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [item.strip() for item in line.split("#")]
        if len(parts) != len(CONFIG_FIELDS):
            print(f"字段数量错误，需要 {len(CONFIG_FIELDS)} 个")
            sys.exit(1)
        accounts.append(dict(zip(CONFIG_FIELDS, parts)))
    if not accounts:
        print("没有有效账号")
        sys.exit(1)
    return accounts


ACCOUNTS = load_accounts()

# ==================== 配置 ====================
LOOP_COUNT = 201
REPORT_DELAY = 1.0

PRIVATE_KEY_BASE64 = "MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAMXGjyS3p+3AVnlBJe5VQ6tC9inh8tVBve4r+yBjC5HQD6th2n3tSyuNVYaNRAFSEq+OENwnwwhjbYUnjLWb+qZscB43K1+4/WlKdvfgwQVXm0ZQ2+jMBf+165UBEEuuWT2WqXeKkkUqPQta5lrt4eFfbo53JcOO4D5fDSGQS5bZAgMBAAECgYAor4I/AXEQXeLsKtTMxMmY77uIPi0gZdfWqUGOFhIJOw4eKZEzGp++I+MWPPVieCnT55vcTmm2zg13uP0fVykmukWqZszG/ZNpPKYleOqnZOqQj7O3au8Ywz18F/pqD++PsUzxRVeXxSOOwmjQ0D2Pe/9yutz62pyiFGAzDsaI6QJBAMn8DeBT3AtcWuONdiHL3yC4NkGJDdyBbMOaWyvrcvUUZr13uS9mZO6pLTN6v9tkmPUdvYxcPTJ9wdGR7NcNPDsCQQD6qluGI2VAlz4s5UoDnelFKrwDPeiruE3I6wsrasK6h37DsAE6OrQgx2dm4yH7ntJHUlJCZ5ay1EBNfEexgQv7AkA1r2vUwxVKY7q4nqHWa8SbgrrRAmePw0qwVreC3erJHyoLk+XBpnqPQKIF+8tAueU5yTTXOLD/WZOJazrDEf5/AkBpwG+Ggu5Xtrcbd8ynA/sDHElf0MGVmNbwOgFnWs42pa1cX6fU6ilOXvIH3TFcF6A9SMS9kThpz9QlHJaek4P7AkAavQillA/wnrha9GsK5UFmzmwNfkjLLW4psAUsXOsqFXWMoxTd0xWuSbuVOzERpbFMBl1VoZQmD9BLSVOTNe+v"

REPORT_BASE_URL = "https://api-dj.palmestore.com"
REPORT_ENDPOINT = "/reading/open/time/report"

WELFARE_BASE_URL = "https://dj.palmestore.com"
WELFARE_QUERY = "/welfare_api/client/task/welfare_list"
WELFARE_RECEIVE = "/welfare_api/client/task/receive"

WITHDRAW_BASE_URL = "https://welfare-user.palmestore.com"
WITHDRAW_ENDPOINT = "/api/user/cashWithdraw"
WITHDRAW_AMOUNT = "2.4"

APP_PACKAGE = "com.ting.jiuli"
APP_ID = "zyb61b8e"
P2 = "703684"
P3 = "160004056"
P25 = "160004056"
P9 = "3"


# ==================== 通用工具 ====================
def load_private_key():
    key_bytes = base64.b64decode(PRIVATE_KEY_BASE64)
    return serialization.load_der_private_key(key_bytes, password=None, backend=default_backend())


def rsa_sha1_sign(private_key, plain_text):
    signature = private_key.sign(
        plain_text.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA1()
    )
    return base64.b64encode(signature).decode()


def make_sign_plain(params):
    sorted_keys = sorted(params.keys())
    parts = []
    for k in sorted_keys:
        v = params[k]
        if v != "":
            parts.append(f"{k}={v}")
    return "&".join(parts)


def build_common_params(account):
    return {
        "pc": "10",
        "p2": P2,
        "p3": P3,
        "p4": "501656",
        "p5": "19",
        "p7": account["p7"],
        "p9": P9,
        "p12": "",
        "p16": account["p16"],
        "p21": "1",
        "p22": "16",
        "p25": P25,
        "p26": "36",
        "p30": "",
        "p31": account["p7"],
        "p33": APP_PACKAGE,
        "p34": account["p34"],
        "p36": "a",
        "firm": account["p34"],
        "d1": "1.0.4",
        "p29": APP_ID,
        "p28": account["p28"],
        "zyeid": account["zyeid"],
        "usr": account["usr"],
        "rgt": "7",
        "p1": account["p1"],
        "ku": account["usr"],
        "kt": account["kt"],
        "p35": account["p35"],
    }


# ==================== Phase 1: 上报 ====================
def build_report_data(today_str):
    return [{
        "type": 6,
        "data": {
            today_str: {
                "d1": [{
                    "bid": "30071455",
                    "format": "",
                    "time": 27,
                    "resType": "listen",
                    "isLogin": 1
                }]
            }
        }
    }]


def run_report_phase(account):
    today_str = date.today().strftime("%Y-%m-%d")
    user = account["usr"]
    print(f"  [{user}] Phase 1 开始: 上报 {LOOP_COUNT} 次")

    for i in range(LOOP_COUNT):
        try:
            params = build_common_params(account)
            data_list = build_report_data(today_str)
            data_str = json.dumps(data_list, separators=(",", ":"), ensure_ascii=False)

            timestamp = str(int(time.time() * 1000))
            sign_params = {k: v for k, v in params.items() if v != ""}
            sign_params["data"] = data_str
            sign_params["user_name"] = user
            sign_params["timestamp"] = timestamp

            plain = make_sign_plain(sign_params)
            private_key = load_private_key()
            sign = rsa_sha1_sign(private_key, plain)

            request_body = {
                "data": data_str,
                "user_name": user,
                "timestamp": timestamp,
                "sign": sign,
            }
            compressed = gzip.compress(
                json.dumps(request_body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            )

            query_string = urlencode(params)
            url = f"{REPORT_BASE_URL}{REPORT_ENDPOINT}?{query_string}"
            headers = {
                "Authorization": f"Bearer {account['kt']}",
                "Content-Type": "text/plain",
                "Accept-Encoding": "gzip",
                "User-Agent": "okhttp/4.12.0",
                "Host": "api-dj.palmestore.com",
            }
            resp = requests.post(url, data=compressed, headers=headers, timeout=15)
            result = resp.json()
            code = result.get("code", "?")

            if i % 50 == 0 or i == LOOP_COUNT - 1:
                print(f"  [{user}] [{i+1}/{LOOP_COUNT}] code={code}")

        except Exception as e:
            print(f"  [{user}] [{i+1}/{LOOP_COUNT}] 错误: {e}")

        if i < LOOP_COUNT - 1:
            time.sleep(REPORT_DELAY)

    print(f"  [{user}] Phase 1 完成")


# ==================== Phase 2: 领取 ====================
def query_welfare_list(account):
    params = build_common_params(account)
    timestamp = str(int(time.time() * 1000))
    sign_dict = dict(params)
    sign_dict["timestamp"] = timestamp
    plain = make_sign_plain(sign_dict)
    private_key = load_private_key()
    sign = rsa_sha1_sign(private_key, plain)
    params["timestamp"] = timestamp
    params["sign"] = sign

    query_string = urlencode(params)
    url = f"{WELFARE_BASE_URL}{WELFARE_QUERY}?{query_string}"
    headers = {
        "Authorization": f"Bearer {account['kt']}",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.12.0",
        "Host": "dj.palmestore.com",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()


def receive_reward(account, sub_task_id):
    query_params = build_common_params(account)
    body_params = {
        "task_type": "246",
        "sub_task_id": sub_task_id,
        "reward_ecpm": "691.0",
        "show_position": "LISTEN_CASH_VIDEO",
    }
    timestamp = str(int(time.time() * 1000))
    sign_dict = {}
    sign_dict.update(query_params)
    sign_dict.update(body_params)
    sign_dict["timestamp"] = timestamp
    plain = make_sign_plain(sign_dict)
    private_key = load_private_key()
    sign = rsa_sha1_sign(private_key, plain)
    body_params["timestamp"] = timestamp
    body_params["sign"] = sign

    query_string = urlencode(query_params)
    url = f"{WELFARE_BASE_URL}{WELFARE_RECEIVE}?{query_string}"
    headers = {
        "Authorization": f"Bearer {account['kt']}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.12.0",
        "Host": "dj.palmestore.com",
    }
    try:
        resp = requests.post(url, data=body_params, headers=headers, timeout=30)
        return resp.json()
    except Exception as e:
        return {"code": -1, "msg": str(e), "body": {}}


def run_claim_phase(account):
    user = account["usr"]
    print(f"  [{user}] Phase 2 开始: 查询 + 领取")

    query_resp = query_welfare_list(account)
    if query_resp.get("code") != 0:
        print(f"  [{user}] 查询失败: {json.dumps(query_resp, ensure_ascii=False)[:200]}")
        return

    body = query_resp.get("body", [])
    if not body:
        print(f"  [{user}] 无 body 数据")
        return

    first_task = body[0]
    reward_list = first_task.get("reward_list", [])
    sub_ids = [item["sub_id"] for item in reward_list if item.get("sub_id")]

    print(f"  [{user}] 任务: {first_task.get('name')} | 共 {len(sub_ids)} 个")

    for idx, sid in enumerate(sub_ids, start=1):
        try:
            r = receive_reward(account, sid)
            code = r.get("code")
            bd = r.get("body", {})
            print(f"  [{user}] [{idx}/{len(sub_ids)}] code={code} reward={bd.get('reward_amount','N/A')} cash={bd.get('cash_num','N/A')}")
        except Exception as e:
            print(f"  [{user}] [{idx}/{len(sub_ids)}] 错误: {e}")
        if idx < len(sub_ids):
            time.sleep(2)

    print(f"  [{user}] Phase 2 完成")


# ==================== Phase 3: 提现 ====================
def cash_withdraw(account, amount=None):
    withdraw_amount = str(amount) if amount else WITHDRAW_AMOUNT
    params = build_common_params(account)
    if account.get("encrypted_usr"):
        params["usr"] = account["encrypted_usr"]

    withdraw_specific = {
        "showContentInStatusBar": "1",
        "smboxid": "",
        "type": "cash_wallet",
        "coin": "",
        "price": withdraw_amount,
        "product_id": "0",
        "item_id": "19970000",
        "method": "2",
        "sign": "",
        "reward_type": "",
        "discount": "false",
        "extract_type": "2",
    }
    params.update(withdraw_specific)

    timestamp = str(int(time.time() * 1000))
    sign_dict = dict(params)
    sign_dict["timestamp"] = timestamp
    plain = make_sign_plain(sign_dict)
    private_key = load_private_key()
    sign = rsa_sha1_sign(private_key, plain)
    params["timestamp"] = timestamp
    params["sign"] = sign

    url = WITHDRAW_BASE_URL + WITHDRAW_ENDPOINT
    headers = {
        "Authorization": "Bearer " + account["kt"],
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip",
        "User-Agent": f"Mozilla/5.0 (Linux; Android 16; {account['p16']} Build/BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/137.0.7151.115 Mobile Safari/537.36 JiuliApp mVersionName/1.0.4 mInnerVersion/{P3}",
        "Origin": WITHDRAW_BASE_URL,
        "X-Requested-With": APP_PACKAGE,
        "Referer": WITHDRAW_BASE_URL + "/jiuli/welfare-package/withdraw/index.html?showContentInStatusBar=1",
        "Host": "welfare-user.palmestore.com",
    }
    try:
        resp = requests.post(url, data=params, headers=headers, timeout=30)
        return resp.json()
    except Exception as e:
        return {"code": -1, "msg": str(e), "body": {}}


def run_withdraw_phase(account):
    user = account["usr"]
    print(f"  [{user}] Phase 3: 提现 {WITHDRAW_AMOUNT} 元")
    try:
        r = cash_withdraw(account)
        code = r.get("code")
        msg = r.get("msg", "")
        if code == 0:
            order_no = r.get("body", {}).get("order_no", "N/A")
            print(f"  [{user}] ✅ 提现成功! 订单: {order_no}")
        else:
            print(f"  [{user}] ❌ 提现失败: code={code} msg={msg}")
    except Exception as e:
        print(f"  [{user}] 提现异常: {e}")


# ==================== 单账号完整流程 ====================
def process_account(account, idx, total):
    user = account["usr"]
    print(f"\n[账号 {idx}/{total}] {user} 开始")
    try:
        run_report_phase(account)
        run_claim_phase(account)
        run_withdraw_phase(account)
        print(f"[账号 {idx}/{total}] {user} 完成 ✓")
    except Exception as e:
        print(f"[账号 {idx}/{total}] {user} 失败: {e}")


# ==================== 主程序 ====================
if __name__ == "__main__":
    total = len(ACCOUNTS)
    print(f"共 {total} 个账号，启动多线程并发执行...")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=total) as executor:
        futures = []
        for idx, acc in enumerate(ACCOUNTS, 1):
            futures.append(executor.submit(process_account, acc, idx, total))
        for future in as_completed(futures):
            future.result()

    print(f"\n{'='*60}")
    print("全部完成!")
    print(f"{'='*60}")