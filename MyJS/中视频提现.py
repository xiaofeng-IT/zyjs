# -*- coding: utf-8 -*-
import requests
import os
import threading

# 配置
BASE_API = "https://x1.zsptv.online"
WITHDRAW_MIN_MONEY = 10  # 提现最低门槛

# 接口地址
LOGIN_API = f"{BASE_API}/api/web/v1/auth/passwordLogin"
PANEL_API = f"{BASE_API}/api/web/v1/dashboard/getPanelData"
BALANCE_API = f"{BASE_API}/api/web/v1/user/wallet/balance/getInfo"
ORDER_API = f"{BASE_API}/api/web/v1/user/wallet/balance/withdrawal/getOrderList"
WITHDRAW_API = f"{BASE_API}/api/web/v1/user/wallet/balance/withdraw"

# 通用请求头
COMMON_HEADERS = {
    "Host": "x1.zsptv.online",
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.115 Mobile Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://zsp.99panel.top",
    "Referer": "https://zsp.99panel.top/",
    "X-Requested-With": "com.mmbox.xbrowser.pro",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

def run_task(username, password):
    """单个账号执行完整任务（并行）"""
    print(f"\n==================== 开始处理账号：{username} ====================")

    def user_login():
        """登录"""
        print("【第一步】执行账号登录")
        post_data = {"mobile": username, "password": password}
        try:
            res = requests.post(LOGIN_API, headers=COMMON_HEADERS, json=post_data, timeout=10)
            res_json = res.json()
            if res_json.get("code") == 0:
                token = res_json["data"]["token"]
                print("✅ 登录成功")
                return token
            else:
                print(f"❌ 登录失败：{res_json.get('message')}")
                return None
        except Exception as e:
            print(f"❌ 登录请求异常：{str(e)}")
            return None

    def get_account_data(token):
        """查询账户数据"""
        print("\n【第二步】查询账户基础数据")
        headers = COMMON_HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        try:
            res = requests.get(PANEL_API, headers=headers, timeout=10)
            res_json = res.json()
            if res_json.get("code") == 0:
                data = res_json["data"]
                print(f"今日广告次数：{data['viewAdCount']}")
                print(f"当前金币数量：{data['incomeScore']}")
                print(f"今日累计收益：¥{data['todayMoney']}")
                return True
            else:
                print(f"❌ 账户数据查询失败")
                return False
        except Exception as e:
            print(f"❌ 数据查询异常：{str(e)}")
            return False

    def check_running_order(token):
        """检查进行中提现订单"""
        print("\n【第三步】核查最新1条提现订单状态")
        headers = COMMON_HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        params = {"page": 1, "limit": 1}
        try:
            res = requests.get(ORDER_API, headers=headers, params=params, timeout=10)
            res_json = res.json()
            if res_json.get("code") == 0:
                order_list = res_json["data"]["data"]
                if not order_list:
                    print("暂无历史提现订单记录")
                    return False
                order = order_list[0]
                status_text = "处理中" if order["status"] == 0 else "已完成"
                print(f"最新订单 | 订单ID：{order['id']} | 金额：¥{order['amount']} | 状态：{status_text}")
                if order["status"] == 0:
                    print("⚠️ 存在处理中订单，禁止提现")
                    return True
                print("✅ 无进行中订单，可提现")
                return False
            else:
                print("❌ 订单查询失败")
                return True
        except Exception as e:
            print(f"❌ 订单查询异常：{str(e)}")
            return True

    def get_withdraw_balance(token):
        """查询可提现余额"""
        print("\n【第四步】查询可提现余额")
        headers = COMMON_HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        try:
            res = requests.get(BALANCE_API, headers=headers, timeout=10)
            res_json = res.json()
            if res_json.get("code") == 0:
                balance = float(res_json["data"]["balance"])
                freeze = float(res_json["data"]["freezeAmount"])
                print(f"✅ 可提现余额：¥{balance}")
                print(f"冻结金额：¥{freeze}")
                return balance
            else:
                print(f"❌ 余额查询失败")
                return 0
        except Exception as e:
            print(f"❌ 余额查询异常：{str(e)}")
            return 0

    def submit_all_withdraw(token, money):
        """全额提现"""
        print(f"\n【第五步】提交全额提现：¥{money}")
        headers = COMMON_HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        post_data = {"amount": str(money)}
        try:
            res = requests.post(WITHDRAW_API, headers=headers, json=post_data, timeout=10)
            res_json = res.json()
            if res_json.get("code") == 0:
                print(f"✅ 提现申请提交成功！¥{money}")
            else:
                print(f"❌ 提现失败：{res_json.get('message')}")
        except Exception as e:
            print(f"❌ 提现异常：{str(e)}")

    # ================== 单个账号执行流程 ==================
    token = user_login()
    if not token:
        print(f"【{username}】登录失败，跳过")
        return

    get_account_data(token)
    has_running = check_running_order(token)
    if has_running:
        print(f"【{username}】存在处理中订单，跳过")
        return

    balance = get_withdraw_balance(token)
    if balance < WITHDRAW_MIN_MONEY:
        print(f"【{username}】余额不足¥{WITHDRAW_MIN_MONEY}，不提现")
        return

    submit_all_withdraw(token, balance)
    print(f"==================== 账号【{username}】任务完成 ====================\n")

if __name__ == "__main__":
    print("========== 多账号并行自动提现脚本 ==========")
    
    # 读取多账号变量（格式：账号#密码@账号#密码）
    account_str = os.getenv("ZS_MOBILE", "")
    if not account_str:
        print("未配置 ZS_MOBILE 变量")
        exit()

    # 分割账号
    account_list = account_str.split("@")
    threads = []

    # 多线程并行执行
    for item in account_list:
        item = item.strip()
        if not item or "#" not in item:
            continue
        user, pwd = item.split("#", 1)
        t = threading.Thread(target=run_task, args=(user, pwd))
        threads.append(t)
        t.start()

    # 等待所有账号完成
    for t in threads:
        t.join()

    print("所有账号执行完毕 ✅")
