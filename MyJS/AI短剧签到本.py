# 环境变量：AIDZ  格式手机号#密码@手机号#密码
import os
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 Version/16.6 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Mi 13) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; vivo X90) Chrome/120.0.0.0 Mobile Safari/537.36"
]
MAX_THREAD = 5
CACHE_DIR = "/ql/config"
CACHE_PATH = os.path.join(CACHE_DIR, "aidz_ua.txt")
LOGIN_URL = "https://www.ai6689.top/api/login"
SIGN_URL = "https://www.ai6689.top/api/clock_today"

# 统计拆分：成功｜当日已签到｜签到失败｜网络异常
stat = {
    "succ": 0,
    "signed": 0,
    "fail": 0,
    "err": 0
}

# 只保留四种结果日志，去掉info信息输出
def log(phone: str, typ: str, msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icon_map = {
        "succ": "✅",
        "signed": "🔘",
        "fail": "❌",
        "err": "⚠️"
    }
    icon = icon_map.get(typ, "·")
    print(f"[{now}] {icon} [{phone:11s}] {msg}")

def load_ua_cache():
    cache = {}
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    phone, ua = line.split("|", 1)
                    cache[phone] = ua
    return cache

def save_cache(cache):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        for k, v in cache.items():
            f.write(f"{k}|{v}\n")

def run_one(phone, pwd, cache):
    sess = requests.Session()
    if phone in cache:
        ua = cache[phone]
    else:
        ua = random.choice(UA_POOL)
        cache[phone] = ua
        save_cache(cache)

    hd_login = {
        "User-Agent": ua,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        res_login = sess.post(LOGIN_URL, data={"phone": phone, "password": pwd}, headers=hd_login, timeout=15).json()
        if res_login.get("status") != 1:
            log(phone, "fail", f"登录失败：{res_login.get('msg','未知错误')}")
            stat["fail"] += 1
            return
        token = res_login["token"]
        ck = ";".join([f"{k}={v}" for k, v in sess.cookies.items()])

        hd_sign = {
            "User-Agent": ua,
            "token": token,
            "Cookie": ck,
            "X-Requested-With": "com.mmbox.xbrowser.pro",
            "Origin": "https://www.ai6689.top",
            "Referer": "https://www.ai6689.top/user/checkin"
        }
        res_sign = sess.post(SIGN_URL, headers=hd_sign, timeout=15).json()
        msg = res_sign.get("msg", "")
        if res_sign.get("status") == 1:
            bonus = res_sign.get("bonus",0)
            total_bonus = res_sign.get("bonus_total",0)
            log(phone, "succ", f"签到成功｜本次+{bonus}元｜累计{total_bonus}元｜{msg}")
            stat["succ"] += 1
        elif "今日已签到" in msg or "已签到" in msg:
            log(phone, "signed", f"当日已完成签到｜{msg}")
            stat["signed"] += 1
        else:
            log(phone, "fail", f"签到失败｜{msg}")
            stat["fail"] += 1
    except Exception as e:
        log(phone, "err", f"请求异常：{str(e)}")
        stat["err"] += 1

if __name__ == "__main__":
    start_time = datetime.now()
    cache_dict = load_ua_cache()
    aidz = os.getenv("AIDZ", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not aidz:
        print(f"[{now}] ⚠️ 未配置环境变量AIDZ")
        exit()
    acc_arr = aidz.split("@")
    valid_list = []
    for acc in acc_arr:
        acc = acc.strip()
        if not acc or "#" not in acc:
            print(f"[{now}] ⚠️ 账号格式异常跳过：{acc}")
            continue
        tel, pw = acc.split("#")
        valid_list.append((tel.strip(), pw.strip()))

    total = len(valid_list)
    print(f"[{now}] 共加载账号：{total} ｜并发线程：{MAX_THREAD}")

    with ThreadPoolExecutor(max_workers=MAX_THREAD) as pool:
        task_list = [pool.submit(run_one, phone, pwd, cache_dict) for phone, pwd in valid_list]
        for future in as_completed(task_list):
            try:
                future.result()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ 线程异常：{e}")

    # 收尾汇总
    end_time = datetime.now()
    cost = (end_time - start_time).total_seconds()
    print("-"*45)
    print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 签到统计汇总")
    print(f"总账号:{total}｜成功:{stat['succ']}｜当日已签:{stat['signed']}｜签到失败:{stat['fail']}｜网络异常:{stat['err']}")
    print(f"脚本总耗时：{cost:.1f}秒")
    print("-"*45)