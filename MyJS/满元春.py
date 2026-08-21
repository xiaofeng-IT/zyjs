#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import time
import random
import hashlib
import json
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import base64
import requests
import urllib3
import threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
urllib3.disable_warnings()
# ===== 阈值 =====
COIN_MAX = 6000
COIN_MIN = 10
# ===== 配置（已按新抓包修改域名）=====
AES_KEY = base64.b64decode("RM6KuwCrgkIcb1lZSvN/4Q==")
AES_IV = base64.b64decode("Db7d7v5gGsFCvwGseQ14Mw==")
APPCODE = "1"
BASE_HOST = "hd.fjqcwl.top"
# ===== 全局代理配置（环境变量名改为yzkck）=====
YZKCK_PROXY = os.getenv("YZKCK_PROXY")
YZKCK_PROXIES = os.getenv("YZKCK_PROXIES")
YZKCK_PROXY_LIST = YZKCK_PROXIES.split('&') if YZKCK_PROXIES else []
# ===== 获取代理（优先级：账号专属 > 全局列表 > 全局单代理）=====
def get_proxy(account_proxy=None):
    if account_proxy and account_proxy.strip():
        return {"http": account_proxy.strip(), "https": account_proxy.strip()}
    if YZKCK_PROXY_LIST:
        p = random.choice(YZKCK_PROXY_LIST)
        return {"http": p, "https": p}
    if YZKCK_PROXY:
        return {"http": YZKCK_PROXY, "https": YZKCK_PROXY}
    return None
# ===== 优化版：带邮箱格式校验，杜绝报错 =====
def send_msg(sendkey, title, content):
    my_sender = "1761791927@qq.com"
    my_auth_code = "wzmztemiagbfehgb"
    my_receiver = sendkey.strip()
    
    # 校验邮箱格式
    if not my_receiver or "@" not in my_receiver:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 接收邮箱格式错误：{my_receiver}")
        return False
    
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = formataddr(["满园春脚本", my_sender])
        msg['To'] = formataddr(["管理员", my_receiver])
        msg['Subject'] = title
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(my_sender, my_auth_code)
        server.sendmail(my_sender, [my_receiver], msg.as_string())
        server.quit()
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 📩 邮箱推送成功")
        return True
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 邮箱推送失败:", e)
        return False
# ===== 工具 =====
def aes_encrypt(data):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    text = json.dumps(data, separators=(',', ':'))
    return base64.b64encode(cipher.encrypt(pad(text.encode(), 16))).decode()
def rand_hex(n):
    return ''.join(random.choice('0123456789abcdef') for _ in range(n))
# ===== 广告生成（已替换为新抓包广告池，两组分组）=====
def gen_ads(user_id):
    group = random.choice([
        [
            ("70","6326615446524767","31594000149","信息流广告","0.60"),
        ],
        [
            ("70","6326615446524767","31594000149","信息流广告","0.60"),
        ]
    ])
    base_time = int(time.time() * 1000)
    current_time = base_time
    ads = []
    for i, ad in enumerate(group):
        delay = random.randint(1000, 8000) if i > 0 else 0
        current_time += delay
        platform = "kuaishou"
        ecpm = random.randint(8000, 15000)
        ads.append({
            "admodel_id": ad[0],
            "admodel_value": ad[1],
            "adplatform_name": platform,
            "adtype_id": ad[0],
            "adtype_name": ad[3],
            "amount": "700，1500",
            "appUserId": "",
            "displayed_at": str(current_time),
            "ecpm": str(ecpm),
            "exchange_rate": "10000",
            "extraInfo": "",
            "loadId": str(__import__('uuid').uuid4()),
            "network_placement_id": ad[2],
            "real_money": f"{ecpm/100000:.5f}",
            "reward_rate": ad[4],
            "user_id": user_id
        })
    return ads
# ===== 广告上报请求（请求头按抓包对齐）=====
def run_once(session):
    ads = gen_ads(session["user_id"])
    details = json.dumps(ads, separators=(',', ':'))
    token = rand_hex(32)
    ts = int(time.time())
    sign = hashlib.md5(f"{token}{details}{ts}".encode()).hexdigest()
    payload = {
        "details": details,
        "signature": sign,
        "timestamp": ts,
        "token": token
    }
    enc = aes_encrypt(payload)
    # 对齐抓包请求头
    headers = {
        "Host": BASE_HOST,
        "Authorization": f"Bearer {session['access_token']}",
        "appcode": APPCODE,
        "Content-Type": "application/json",
        "User-Agent": "okhttp/4.9.0",
        "accept-language": "zh-CN",
        "accept-encoding": "gzip"
    }
    try:
        r = requests.post(
            f"https://{BASE_HOST}/g/GetAdrewardCoins.ashx",
            data=enc,
            headers=headers,
            proxies=get_proxy(session["proxy"]),
            timeout=10,
            verify=False
        ).json()
        if r.get("Code") == 200:
            return r["Data"]["coins"]
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 请求异常:", e)
    return None
# ===== 单账号执行逻辑（封装成函数，用于多线程）=====
def run_account(note, account):
    session = {
        "access_token": account["access_token"],
        "user_id": account["user_id"],
        "proxy": account["proxy"],
        "sendkey": account["sendkey"]
    }
    proxy_info = account["proxy"] if account["proxy"] else "全局/无代理"
    push_info = "已开启" if account["sendkey"] else "未开启"
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{note}] user_id:{session['user_id']} | 代理: {proxy_info} | 推送: {push_info}")
    last_coins = -1
    last_state = ""
    while True:
        coins = run_once(session)
        if coins is None:
            continue
        if coins >= COIN_MAX:
            state = "已达上限"
            # 生成随机 60-70 秒等待时间
            wait_time = random.uniform(60, 70)
            if last_state != "已达上限":
                send_msg(session["sendkey"], "满园春金币上限提醒", f"{note}\nuser_id:{session['user_id']}\n当前金币：{coins}\n{wait_time:.1f}秒后自动继续")
            # 打印日志，显示具体等待秒数
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{note}] 金币:{coins} | 状态:{state} | 等待{wait_time:.1f}秒后继续")
            last_coins = coins
            last_state = state
            time.sleep(wait_time)
        elif coins <= COIN_MIN:
            state = "恢复运行"
            if coins != last_coins or state != last_state:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{note}] 金币:{coins} | 状态:{state}")
            last_coins = coins
            last_state = state
            time.sleep(random.uniform(15, 21))
        else:
            state = "运行中"
            if coins != last_coins or state != last_state:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{note}] 金币:{coins} | 状态:{state}")
            last_coins = coins
            last_state = state
            time.sleep(random.uniform(15, 21))
# ===== 主逻辑（多线程并发）=====
def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 脚本启动【多线程并发版】")
    accounts = []
    # 环境变量正则改为 yzkck 开头
    pattern = re.compile(r'^YZKCK\d*$')
    for key in sorted(os.environ.keys(), key=lambda x: (not pattern.match(x), x)):
        if pattern.match(key):
            account_info = os.getenv(key).strip()
            if not account_info:
                continue
            parts = account_info.split('#')
            # 格式：备注#token#user_id#proxy#sendkey
            if len(parts) != 5:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 环境变量 {key} 格式错误！正确格式：备注#token#user_id#proxy#sendkey")
                continue
            accounts.append({
                "note": parts[0],
                "access_token": parts[1],
                "user_id": parts[2],
                "proxy": parts[3],
                "sendkey": parts[4]
            })
    if not accounts:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ 未检测到任何有效YZKCK环境变量！")
        return
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 加载到 {len(accounts)} 个账号，开始并发执行\n")
    # 多线程启动所有账号
    threads = []
    for idx, account in enumerate(accounts, 1):
        t = threading.Thread(target=run_account, args=(account["note"], account))
        threads.append(t)
        t.start()
    # 等待所有线程执行
    for t in threads:
        t.join()
if __name__ == "__main__":
    main()
