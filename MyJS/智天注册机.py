#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智天银行注册机 - 青龙面板环境变量说明
所需环境变量：
  ZTYH：邀请码#数量，多组换行分隔
  示例：123456#5
       123456#3

  LZ：实名列表，格式：姓名----身份证，多组换行分隔
  示例：张三----110101199001011234
       李四----110101199001011234

  PROXY_API : 代理提取接口地址（必须填写，不允许直连）
  示例：http://api3.ydaili.cn/tools/MeasureApi.ashx?action=EAPI&secret=xxx&number=1&orderId=xxx&format=txt&type=1&split=3
  
"""

import requests
import random
import time
import os
import sys
import string
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REGISTER_DELAY_MIN = 300
REGISTER_DELAY_MAX = 500
REGISTER_FAIL_DELAY = 3
LETTER_COUNT_MIN = 2
LETTER_COUNT_MAX = 3
NUMBER_COUNT_MIN = 6
NUMBER_COUNT_MAX = 8

SAVE_FILE = "智天银行已注册账号.txt"
USED_REALNAME_FILE = "智天银行已用料子.txt"

BASE_URL = "https://yq.ztyha001.com"

REQUEST_RETRY = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
CONCURRENT_WORKERS = 5
PROXY_RETRY = 5
PROXY_TEST_TIMEOUT = 10

# ==================== 代理接口从环境变量读取（必须配置） ====================
PROXY_API_URL = os.getenv("PROXY_API", "")

if not PROXY_API_URL:
    print("[ERROR] 未设置 PROXY_API 环境变量，脚本无法运行，请配置代理接口地址后重试。")
    sys.exit(1)

# ==================== 随机 UA 与指纹 ====================
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

# ==================== 核心逻辑 ====================
def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def load_used_realname():
    if not os.path.exists(USED_REALNAME_FILE): return set()
    with open(USED_REALNAME_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def add_used_realname(id_card):
    with open(USED_REALNAME_FILE, "a", encoding="utf-8") as f:
        f.write(id_card + "\n")
    log(f"🚫 身份证 {id_card} 已加入黑名单")

def parse_ztyh():
    env = os.getenv("ZTYH", "")
    if not env:
        log("❌ 请配置环境变量 ZTYH")
        sys.exit(1)
    tasks = []
    for line in env.strip().splitlines():
        if not line: continue
        if "#" not in line:
            log(f"❌ ZTYH 格式错误：{line}")
            sys.exit(1)
        invite, num = line.split("#", 1)
        try:
            tasks.append({"invite_code": invite.strip(), "reg_count": int(num.strip())})
        except ValueError:
            log(f"❌ 数量必须为数字：{line}")
            sys.exit(1)
    log(f"📋 解析到 {len(tasks)} 组邀请码任务")
    return tasks

def parse_lz():
    env = os.getenv("LZ", "")
    if not env:
        log("❌ 请配置环境变量 LZ")
        sys.exit(1)
    real_list = []
    for line in env.strip().splitlines():
        if not line: continue
        if "----" not in line:
            log(f"❌ LZ 格式错误：{line}")
            sys.exit(1)
        name, idcard = line.split("----", 1)
        real_list.append((name.strip(), idcard.strip()))
    if not real_list:
        log("❌ LZ 未解析到有效实名")
        sys.exit(1)
    used = load_used_realname()
    available = [item for item in real_list if item[1] not in used]
    log(f"📋 可用实名：{len(available)}/{len(real_list)}")
    return available

def random_phone():
    seg = random.choice(["135","136","138","139","150","151","152","157","158","159",
                         "172","178","182","183","184","187","188","195","197","198",
                         "130","131","132","145","155","156","166","175","176","185",
                         "186","196","133","149","153","173","180","181","189",
                         "190","191","193","199","192"])
    return seg + ''.join(random.choices("0123456789", k=8))

def generate_password():
    chars = random.choices(string.ascii_lowercase, k=random.randint(2,3)) + \
            random.choices(string.digits, k=random.randint(6,8))
    random.shuffle(chars)
    return ''.join(chars)

def get_proxy():
    """从 PROXY_API 获取代理，若失败则返回 None（调用处会跳过该账号）"""
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
            log(f"🌐 获取代理成功并验证通过：{proxy_str}")
            return proxy
        except Exception:
            time.sleep(2)
    log("❌ 代理获取失败")
    return None

def get_session(proxy):
    if proxy is None:
        return None
    s = requests.Session()
    s.mount("http://", HTTPAdapter(max_retries=REQUEST_RETRY))
    s.mount("https://", HTTPAdapter(max_retries=REQUEST_RETRY))
    s.proxies.update(proxy)
    return s

def save_account(data):
    with open(SAVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"【上级邀请码:{data['super_invite']}】手机:{data['phone']} 密码:{data['password']} Token:{data['token']} 个人邀请码:{data.get('invite_code','')}\n")
    log(f"💾 账号已保存：{data['phone']}")

def register(session, mobile, password, invite_code, ua, sec_ch_ua, accept_lang):
    url = f"{BASE_URL}/api/user/register"
    headers = {
        "User-Agent": ua,
        "Accept-Language": accept_lang,
        "Sec-Ch-Ua": sec_ch_ua,
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }
    payload = {"mobile": mobile, "password": password, "invite_code": invite_code}
    resp = session.post(url, json=payload, headers=headers, timeout=30)
    data = resp.json()
    if data.get("code") == 1:
        userinfo = data.get("data", {}).get("userinfo", {})
        return True, userinfo.get("token"), userinfo.get("invite_code", ""), data.get("msg")
    return False, None, None, data.get("msg", "注册失败")

def realname(session, token, real_name, id_card, ua, sec_ch_ua, accept_lang):
    url = f"{BASE_URL}/api/user/realnameSubmit"
    headers = {
        "User-Agent": ua,
        "Accept-Language": accept_lang,
        "Sec-Ch-Ua": sec_ch_ua,
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Content-Type": "application/json",
        "token": token,
        "Accept": "*/*",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }
    payload = {"realname": real_name, "idcard": id_card, "idcard_front": "", "idcard_back": ""}
    resp = session.post(url, json=payload, headers=headers, timeout=30)
    data = resp.json()
    if data.get("code") == 1:
        return True, data.get("msg", "实名成功")
    return False, data.get("msg", "实名失败")

def sign(session, token, ua, sec_ch_ua, accept_lang):
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
    resp = session.get(url, headers=headers, timeout=30)
    data = resp.json()
    if data.get("code") == 1:
        return True, data.get("msg", "签到成功")
    return False, data.get("msg", "签到失败")

def single_invite_task(invite_code, reg_total, real_queue):
    success = 0
    for i in range(reg_total):
        log(f"\n----------【邀请码 {invite_code}】第 {i+1}/{reg_total} 个账号 ----------")
        try:
            real_name, id_card = real_queue.get(timeout=1)
        except queue.Empty:
            log("❌ 实名队列已空")
            break
        log(f"📝 分配实名：{real_name} {id_card}")

        ua = random_ua()
        sec_ch_ua = random_sec_ch_ua()
        accept_lang = random_accept_language()

        proxy = get_proxy()
        if proxy is None:
            log("❌ 无法获取代理，跳过本账号")
            continue
        session = get_session(proxy)
        if session is None:
            log("❌ 创建会话失败")
            continue

        phone = random_phone()
        password = generate_password()
        log(f"📱 手机号：{phone}，密码：{password}")

        ok, token, invite_self, msg = register(session, phone, password, invite_code, ua, sec_ch_ua, accept_lang)
        if not ok:
            log(f"❌ 注册失败：{msg}")
            time.sleep(REGISTER_FAIL_DELAY)
            continue
        log(f"✅ 注册成功，Token: {token[:20]}... 个人邀请码：{invite_self}")

        delay = random.randint(10, 20)
        log(f"⏳ 等待 {delay}s 后实名...")
        time.sleep(delay)

        ok, msg = realname(session, token, real_name, id_card, ua, sec_ch_ua, accept_lang)
        if not ok:
            log(f"❌ 实名失败：{msg}")
            if "已实名" in msg or "已存在" in msg:
                add_used_realname(id_card)
            continue
        log(f"✅ 实名成功：{msg}")
        add_used_realname(id_card)

        delay = random.randint(15, 30)
        log(f"⏳ 等待 {delay}s 后签到...")
        time.sleep(delay)

        ok, msg = sign(session, token, ua, sec_ch_ua, accept_lang)
        if ok:
            log(f"✅ 签到成功：{msg}")
        else:
            log(f"❌ 签到失败：{msg}")

        save_account({
            "super_invite": invite_code,
            "phone": phone,
            "password": password,
            "token": token,
            "invite_code": invite_self
        })
        success += 1

        if i < reg_total - 1:
            delay = random.randint(REGISTER_DELAY_MIN, REGISTER_DELAY_MAX)
            log(f"⏳ 下一个账号延时 {delay} 秒")
            time.sleep(delay)

    log(f"✅ 邀请码 {invite_code} 任务完成，成功 {success}/{reg_total}")

def main():
    log("========== 智天银行注册机启动 ==========")
    log(f"ℹ️ 代理接口已配置：{PROXY_API_URL}")

    real_list = parse_lz()
    if not real_list:
        log("❌ 无可用的实名")
        sys.exit(1)
    real_queue = queue.Queue()
    for item in real_list:
        real_queue.put(item)
    log(f"📦 实名队列已初始化，共 {real_queue.qsize()} 个可用实名")

    tasks = parse_ztyh()
    if not tasks:
        log("❌ 无有效任务")
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(single_invite_task, t["invite_code"], t["reg_count"], real_queue) for t in tasks]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                log(f"❌ 任务异常：{e}")

    log("\n========== 所有任务结束 ==========")

if __name__ == "__main__":
    main()