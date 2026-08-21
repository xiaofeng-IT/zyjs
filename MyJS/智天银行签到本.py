#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智天银行签到脚本 - 青龙面板环境变量说明
所需环境变量：
  PROXY_API : 代理提取接口地址（必须填写，不允许直连）
  示例：http://api3.ydaili.cn/tools/MeasureApi.ashx?action=EAPI&secret=xxx&number=1&orderId=xxx&format=txt&type=1&split=3

账号文件：
  默认读取同目录下的 智天银行已注册账号.txt
  格式示例：【上级邀请码:0695278】手机:15576364589 密码:aa123456 Token:eea6496a-... 个人邀请码:3986540

签到间隔：固定 15~30 秒（随机）
"""

import requests
import random
import time
import os
import sys
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==================== 环境变量 ====================
PROXY_API_URL = os.getenv("PROXY_API", "")
if not PROXY_API_URL:
    print("[ERROR] 未设置 PROXY_API 环境变量，脚本无法运行，请配置代理接口地址后重试。")
    sys.exit(1)

# ==================== 文件路径 ====================
ACCOUNT_FILE = "智天银行已注册账号.txt"
BASE_URL = "https://yq.ztyha001.com"

# ==================== 请求配置 ====================
REQUEST_RETRY = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
PROXY_RETRY = 5
PROXY_TEST_TIMEOUT = 10
REQUEST_TIMEOUT = 30

# ==================== 签到间隔固定 15~30 秒 ====================
CHECKIN_INTERVAL_MIN = 15
CHECKIN_INTERVAL_MAX = 30

# ==================== 随机 UA 与指纹（与注册机保持一致） ====================
_ANDROID_MODELS = [
    "SM-G991B", "SM-G996B", "SM-G998B", "SM-S901B", "SM-S906B", "SM-S911B",
    "SM-S916B", "SM-S921B", "SM-S926B", "SM-S928B", "SM-A525F", "SM-A725F",
    "SM-A135F", "SM-A335F", "SM-A546B", "SM-N981B", "SM-F721B", "SM-F936B",
    "SM-X800", "SM-S9010",
    "M2101K6G", "M2102J2SC", "M2012K11AC", "2107119DC", "2109119BC",
    "2201122C", "2201123C", "22081212C", "2210132C", "2211133C",
    "23013RK75C", "23049PCD8G", "23078RKD5C", "23090RA98C", "23127PN0CC",
    "2312DRA50C", "24031PN0DC", "2201117TG", "220333QNY", "23046PNC9C",
    "VOG-L29", "ELE-L29", "TAS-AL00", "LIO-AL00", "ELS-AN00", "ANG-AN00",
    "NOP-AN00", "BKL-AL20", "VCE-AL00", "LYA-AL00", "LIO-L29", "WAS-LX1A",
    "TNA-AN00", "JLH-AN00", "LGE-AN00", "FNE-AN00", "PGT-AN00", "AGM3-AN00",
    "BRU-AN00", "ALN-AL00", "BON-AL00", "HJC-AN00", "ANY-AN00", "BKL-L21",
    "CPH2305", "CPH2409", "CPH2499", "CPH2599", "CPH2609", "PFDM00",
    "PGJM10", "PHQ110", "PCKM80", "PBEM00", "PDEM30", "PEDM00", "CPH2583",
    "V2180A", "V2202A", "V2309A", "V2148A", "V2219A", "V2230A", "V2241A",
    "V2054A", "V2029", "V2001A", "V2253A", "V2203A", "V2307A", "V2329A",
    "V2339A", "V2350A", "V2301A",
    "IN2011", "IN2013", "LE2121", "LE2123", "CPH2413", "CPH2451", "CPH2471",
    "CPH2487", "CPH2423",
    "Pixel 5", "Pixel 6", "Pixel 6 Pro", "Pixel 7", "Pixel 7 Pro", "Pixel 7a",
    "Pixel 8", "Pixel 8 Pro", "Pixel 8a", "Pixel Fold",
    "RMX2202", "RMX3085", "RMX3300", "RMX3370", "RMX3686", "RMX3706",
    "RMX3851", "RMX3930",
    "XT2225-1", "XT2337-2", "XT2125-4", "XT2313-1", "XT2343-1", "XT2363-1",
    "XT2175-2", "XT2201-2", "XT2321-3",
    "NX669J", "XQ-BC72", "XQ-CT72", "TA-1379", "ZS660KL", "A2322",
    "TB-J606F", "Infinix X6833B", "TECNO PHANTOM X2", "SM-A515F",
    "SM-M515F", "SM-G780F", "Redmi Note 11", "Redmi Note 12 Pro",
    "M2010J19SG", "M2007J3SY", "20233G7BI", "2311DRK48G", "CPH2591",
]

_ANDROID_BUILD = {
    "10": ["QP1A.190711.020", "QQ3A.200805.001"],
    "11": ["RP1A.200720.011", "RP1A.201005.001"],
    "12": ["SP1A.210812.016", "SQ3A.220705.003"],
    "12L": ["SQ1A.220205.002"],
    "13": ["TP1A.220624.014", "TQ3A.230805.001"],
    "14": ["UP1A.231005.007", "UQ1A.240205.002"],
    "15": ["AP2A.240805.005", "BP1A.250405.007"],
}

_ANDROID_VERSIONS = list(_ANDROID_BUILD.keys())
_CHROME_VERSIONS = [f"{v}.0.0.0" for v in range(105, 145)]
_CHROME_MAJOR_VERSIONS = list(range(105, 145))

ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.5",
    "zh;q=0.9,en-US;q=0.8,en;q=0.7",
]

def random_ua():
    model = random.choice(_ANDROID_MODELS)
    ver = random.choice(_ANDROID_VERSIONS)
    build = random.choice(_ANDROID_BUILD[ver])
    chrome = random.choice(_CHROME_VERSIONS)
    return (f"Mozilla/5.0 (Linux; Android {ver}; {model} Build/{build}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} "
            f"Mobile Safari/537.36")

def random_accept_language():
    return random.choice(ACCEPT_LANGUAGES)

def random_sec_ch_ua():
    major = random.choice(_CHROME_MAJOR_VERSIONS)
    return f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not A(Brand";v="24"'

# ==================== 日志 ====================
def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ==================== 代理获取 ====================
def get_proxy():
    for _ in range(PROXY_RETRY):
        try:
            resp = requests.get(PROXY_API_URL, timeout=15)
            proxy_str = resp.text.strip()
            if not proxy_str or ":" not in proxy_str:
                continue
            proxy = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
            test_session = requests.Session()
            test_session.proxies.update(proxy)
            test_session.get(BASE_URL, timeout=PROXY_TEST_TIMEOUT)
            return proxy
        except Exception:
            time.sleep(2)
    return None

def get_session(proxy):
    if proxy is None:
        return None
    s = requests.Session()
    s.mount("http://", HTTPAdapter(max_retries=REQUEST_RETRY))
    s.mount("https://", HTTPAdapter(max_retries=REQUEST_RETRY))
    s.proxies.update(proxy)
    return s

# ==================== 签到接口 ====================
def do_checkin(session, token, ua, sec_ch_ua, accept_lang):
    url = f"{BASE_URL}/api/checkin/sign"
    headers = {
        "User-Agent": ua,
        "Accept-Language": accept_lang,
        "Sec-Ch-Ua": sec_ch_ua,
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "token": token,
        "Accept": "*/*",
        "Referer": f"{BASE_URL}/",
    }
    try:
        resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get("code") == 1:
            return True, data.get("msg", "签到成功")
        else:
            return False, data.get("msg", "签到失败")
    except Exception as e:
        return False, str(e)

# ==================== 解析账号文件 ====================
def parse_accounts(file_path):
    if not os.path.exists(file_path):
        log(f"❌ 账号文件 {file_path} 不存在")
        return []
    accounts = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            phone_match = re.search(r"手机:(\d+)", line)
            token_match = re.search(r"Token:([A-Za-z0-9_\-\.]+)", line)
            invite_match = re.search(r"个人邀请码:(\w+)", line)
            if phone_match and token_match:
                accounts.append({
                    "phone": phone_match.group(1),
                    "token": token_match.group(1),
                    "invite_code": invite_match.group(1) if invite_match else ""
                })
    return accounts

# ==================== 主流程 ====================
def main():
    log("========== 智天银行签到脚本启动 ==========")
    log(f"ℹ️ 代理接口已配置：{PROXY_API_URL}")

    accounts = parse_accounts(ACCOUNT_FILE)
    if not accounts:
        log("❌ 未找到任何有效账号，请检查账号文件格式")
        sys.exit(1)
    log(f"📋 共读取到 {len(accounts)} 个账号")

    success_count = 0
    fail_count = 0

    for idx, acc in enumerate(accounts, 1):
        log(f"\n---------- 第 {idx}/{len(accounts)} 个账号 ----------")
        log(f"📱 手机号：{acc['phone']}")

        proxy = get_proxy()
        if proxy is None:
            log("❌ 无法获取代理，跳过本账号")
            fail_count += 1
            continue
        session = get_session(proxy)
        if session is None:
            log("❌ 创建会话失败，跳过本账号")
            fail_count += 1
            continue

        ua = random_ua()
        sec_ch_ua = random_sec_ch_ua()
        accept_lang = random_accept_language()

        ok, msg = do_checkin(session, acc['token'], ua, sec_ch_ua, accept_lang)
        if ok:
            log(f"✅ 签到成功：{msg}")
            success_count += 1
        else:
            log(f"❌ 签到失败：{msg}")
            fail_count += 1

        if idx < len(accounts):
            delay = random.randint(CHECKIN_INTERVAL_MIN, CHECKIN_INTERVAL_MAX)
            log(f"⏳ 等待 {delay} 秒后处理下一个账号...")
            time.sleep(delay)

    log(f"\n========== 签到完成，成功 {success_count}，失败 {fail_count} ==========")

if __name__ == "__main__":
    main()