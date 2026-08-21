import requests
import os

BASE_URL = "https://api.robomind.vip"
account_raw = os.getenv("ronomind", "")
if not account_raw:
    print("❌ 环境变量 ronomind 未配置！格式：邮箱#密码&邮箱#密码")
    exit(1)

account_groups = account_raw.split("&")

# 登录请求头
login_headers = {
    "user-agent": "Dart/3.12 (dart:io)",
    "language": "1",
    "accept-encoding": "gzip",
    "content-type": "application/json",
    "host": "api.robomind.vip"
}
# 初始化、训练专用请求头（还原抓包content-length:0）
train_headers_base = {
    "user-agent": "Dart/3.12 (dart:io)",
    "language": "1",
    "accept-encoding": "gzip",
    "content-length": "0",
    "host": "api.robomind.vip",
    "content-type": "application/json"
}

def single_login(email: str, pwd: str):
    """账号登录获取Token"""
    url = f"{BASE_URL}/api/v1/auth/login"
    payload = {"email": email, "password": pwd}
    try:
        resp = requests.post(url, headers=login_headers, json=payload, timeout=15)
        res_data = resp.json()
        if res_data.get("code") == 0:
            token = res_data["data"]["token"]
            print(f"✅【{email}】登录成功，Token片段：{token[:35]}...")
            return token
        else:
            print(f"❌【{email}】登录失败：{res_data}")
            return None
    except Exception as e:
        print(f"⚠️【{email}】登录请求异常：{str(e)}")
        return None

def mock_app_browse(token: str, email: str):
    """模拟APP浏览：汇率、公告、任务接口，降低风控"""
    headers = train_headers_base.copy()
    headers.pop("content-length")
    headers["authorization"] = token
    headers["token"] = token
    try:
        # 1. 汇率接口
        requests.get(f"{BASE_URL}/api/v1/currency-rates", headers=headers, timeout=10)
        # 2. 公告接口
        requests.get(f"{BASE_URL}/api/v1/announcements", headers=headers, timeout=10)
        # 3. 任务列表接口
        requests.get(f"{BASE_URL}/api/v1/mining/tasks", headers=headers, timeout=10)
        print(f"ℹ️【{email}】模拟APP浏览请求完成")
    except Exception:
        pass

def mining_initialize(token: str, email: str):
    """挖矿初始化（严格匹配抓包POST /api/v1/mining/initialize）"""
    init_url = f"{BASE_URL}/api/v1/mining/initialize"
    headers = train_headers_base.copy()
    headers["authorization"] = token
    headers["token"] = token
    try:
        # 空字符串data，严格匹配抓包content-length:0
        resp = requests.post(init_url, headers=headers, data="", timeout=15)
        res_data = resp.json()
        if res_data.get("code") == 0 and res_data["data"]["initialized"] is True:
            print(f"✅【{email}】初始化完成，initialized={res_data['data']['initialized']}")
            return True
        else:
            print(f"❌【{email}】初始化失败：{res_data}")
            return False
    except Exception as e:
        print(f"⚠️【{email}】初始化请求异常：{str(e)}")
        return False

def do_train(token: str, email: str):
    """执行每日训练签到"""
    url = f"{BASE_URL}/api/v1/mining/train"
    headers = train_headers_base.copy()
    headers["authorization"] = token
    headers["token"] = token
    try:
        resp = requests.post(url, headers=headers, data="", timeout=15)
        res_data = resp.json()
        if res_data.get("code") == 0:
            if res_data["data"]["has_trained_today"] is True:
                print(f"ℹ️【{email}】今日已完成训练，无需重复执行")
            else:
                print(f"✅【{email}】签到完成 | 基础150 ROBO + 释放4 ROBO")
                print(f"    训练状态：{res_data['data']['status']}")
        else:
            print(f"❌【{email}】签到失败：{res_data}")
        print()
    except Exception as e:
        print(f"⚠️【{email}】签到异常：{str(e)}\n")

if __name__ == "__main__":
    for idx, item in enumerate(account_groups, 1):
        item = item.strip()
        if not item:
            continue
        try:
            email, password = item.split("#")
            email = email.strip()
            password = password.strip()
            print(f"===== 开始处理第{idx}号账号：{email} =====")
            tk = single_login(email, password)
            if tk:
                mock_app_browse(tk, email)
                # 固定顺序：先执行初始化，初始化成功才执行签到
                init_result = mining_initialize(tk, email)
                if init_result:
                    do_train(tk, email)
        except ValueError:
            print(f"❌ 第{idx}组账号格式错误，格式：邮箱#密码：{item}\n")