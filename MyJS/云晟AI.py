"""
云晟AI 批量注册/登录签到 双模式脚本

环境变量说明：
1. KENUOZN_MAIN
   主配置：0#0#邀请码#注册数量
   示例：0#0#1000#10

2. KENUOZN_MODE
   reg = 注册模式+登陆签到
   sign = 登录签到模式
"""

import os
import sys
import random
import re
import requests
import time
import string
from datetime import datetime

# ===================== 全局基础配置 =====================
MOBILE_SEG = [
    "135","136","138","139","150","151","152","157","158","159",
    "172","178","182","183","184","187","188","195","197","198",
    "130","131","132","145","155","156","166","175","176","185",
    "186","196","133","149","153","173","177","180","181","189",
    "190","191","193","199","192"
]

SURNAME = [
    "张", "李", "王", "刘", "陈", "杨", "黄", "赵", "周", "吴", "徐", "孙", "马", "朱", "胡",
    "林", "郭", "何", "高", "罗", "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹",
    "彭", "曾", "萧", "蔡", "潘", "田", "董", "袁", "于", "余", "叶", "蒋", "苏", "魏", "程",
    "丁", "沈", "姚", "钟", "姜", "崔", "谭", "廖", "陆", "方", "金", "邱", "夏", "侯", "孟",
    "樊", "焦", "白", "毛", "秦", "江", "史", "顾", "贺", "段", "郝", "邵", "钱", "严", "尹",
    "武", "孔", "黎", "汤", "易", "施", "洪", "庞", "屈", "葛", "纪", "盛", "童", "温", "柴",
    "骆", "耿", "蓝", "臧", "包", "代", "欧阳", "谷", "单"
]
NAME = [
    "伟", "芳", "娜", "敏", "静", "强", "磊", "军", "洋", "勇", "艳", "杰", "涛", "明", "超",
    "浩", "宇", "辰", "轩", "泽", "睿", "博", "恒", "凯", "航", "峰", "辉", "鹏", "旭", "霖",
    "宸", "骏", "毅", "鑫", "彬", "松", "波", "坤", "哲", "诚", "扬", "翰", "川", "岩", "昭",
    "欣", "萱", "雨", "彤", "瑶", "琪", "雯", "琳", "菲", "怡", "妍", "茹", "玥", "晴", "曼",
    "钰", "沁", "岚", "娇", "芮", "茉", "凝", "雪", "婵", "姿", "洛", "茵", "淳", "朗", "钧",
    "屹", "骁", "琮", "朔", "翊", "嵩", "岑", "桁", "诺", "幂", "裳", "绾", "杉", "缨", "檀",
    "穗", "芍", "霏", "泠", "胭", "菀", "柠"
]


REQ_TIMEOUT = 15
# 注册账号完成后休眠区间
SLEEP_MIN = 120
SLEEP_MAX = 300
# 签到账号完成后延时 10~15s
SIGN_DELAY_MIN = 10
SIGN_DELAY_MAX = 15
# 代理API重试间隔
PROXY_RETRY_MIN = 3
PROXY_RETRY_MAX = 8
# 代理接口地址
PROXY_API_URL = "http://api3.ydaili.cn/tools/MeasureApi.ashx?action=EAPI&secret=051A6FFFD59786AB06F02255643AAE5C84C65D66F6131905&number=1&orderId=SH20260603035858921&format=txt&type=1&split=3"
# 账号存储文件
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNT_FILE_NAME = "注册列表.txt"
ACCOUNT_FILE_PATH = os.path.join(SCRIPT_DIR, ACCOUNT_FILE_NAME)

# ===================== 美化日志工具（统一格式+时间戳） =====================
def get_time_stamp():
    return datetime.now().strftime("%H:%M:%S")

def log_split(title=""):
    """打印分割线"""
    if title:
        print(f"\n[{get_time_stamp()}] ===== {title} =====\n")
    else:
        print(f"\n[{get_time_stamp()}] ----------------------------------------")

def log_info(msg):
    print(f"[{get_time_stamp()}] [INFO]     {msg}")

def log_success(msg):
    print(f"[{get_time_stamp()}] [SUCCESS]  {msg}")

def log_warn(msg):
    print(f"[{get_time_stamp()}] [WARN]     {msg}")

def log_error(msg):
    print(f"[{get_time_stamp()}] [ERROR]    {msg}")

# ===================== 工具函数 =====================
def gen_random_phone() -> str:
    seg = random.choice(MOBILE_SEG)
    suffix = "".join(str(random.randint(1,9)) for _ in range(8))
    return seg + suffix

def gen_random_password() -> str:
    total_len = random.randint(8, 12)
    letters = string.ascii_letters
    head_cnt = random.choice([2, 3])
    digit_cnt = total_len - head_cnt
    head = "".join(random.sample(letters, head_cnt))
    tail = "".join(random.choices(string.digits, k=digit_cnt))
    return head + tail

def get_proxy_ip():
    while True:
        try:
            resp = requests.get(PROXY_API_URL, timeout=REQ_TIMEOUT)
            resp.raise_for_status()
            proxy_text = resp.text.strip()
            if not proxy_text or ":" not in proxy_text:
                log_warn("代理API返回无效IP，等待几秒重新获取")
                time.sleep(random.randint(PROXY_RETRY_MIN, PROXY_RETRY_MAX))
                continue
            ip, port = proxy_text.split(":")
            proxy_addr = f"http://{ip}:{port}"
            proxies = {"http": proxy_addr, "https": proxy_addr}
            log_info(f"成功获取代理IP → {proxy_addr}")
            return proxies
        except Exception as e:
            log_error(f"代理获取失败: {str(e)}，稍后重试")
            time.sleep(random.randint(PROXY_RETRY_MIN, PROXY_RETRY_MAX))

def get_random_name():
    return random.choice(SURNAME) + random.choice(NAME) + random.choice(NAME)

def append_single_account(phone, pwd, realname, alipay, invite):
    reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{phone}|{pwd}|{realname}|{alipay}|{invite}|{reg_time}\n"
    try:
        with open(ACCOUNT_FILE_PATH, "a+", encoding="utf-8") as f:
            f.seek(0)
            if not f.read().strip():
                f.write("===== 注册账号总列表 | 手机号|密码|姓名|支付宝|邀请码|注册时间 =====\n")
                f.write("--------------------------------------------------------------------------\n")
            f.write(line)
        log_success(f"账号 {phone} 已持久化保存至 {ACCOUNT_FILE_NAME}")
    except Exception as e:
        log_error(f"写入账号文件异常: {str(e)}")

def load_all_accounts():
    all_acc = []
    if not os.path.exists(ACCOUNT_FILE_PATH):
        log_warn(f"{ACCOUNT_FILE_NAME} 文件不存在，暂无历史账号")
        return all_acc
    try:
        with open(ACCOUNT_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if "|" in line and not line.startswith(("=", "-")):
                parts = line.split("|")
                if len(parts) >= 2:
                    phone = parts[0].strip()
                    pwd = parts[1].strip()
                    if len(phone) == 11 and phone.isdigit():
                        all_acc.append((phone, pwd))
        unique_list = []
        seen_phone = set()
        for p, w in all_acc:
            if p not in seen_phone:
                seen_phone.add(p)
                unique_list.append((p, w))
        return unique_list
    except Exception as e:
        log_error(f"读取账号文件失败: {str(e)}")
        return []

# ===================== 接口请求函数 =====================
def get_reg_sms(session, phone, proxies):
    url = "http://yun.kenuozn.cn/user/reg_sms"
    headers = {
        "Host": "yun.kenuozn.cn",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://yun.kenuozn.cn",
        "Referer": "http://yun.kenuozn.cn/user/reg/u/1714.html"
    }
    data = {"phone": phone}
    try:
        resp = session.post(url, headers=headers, data=data, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        res = resp.json()
        msg = str(res.get("info", ""))
        # 识别已注册关键词
        if "手机号已存在" in msg or "已注册" in msg or "手机号存在" in msg:
            log_warn(f"[{phone}] 验证码接口检测：手机号已存在")
            return False, None, False, "registered"
        if res.get("status") == 1:
            code = res["info"].split("：")[-1].strip()
            log_info(f"[{phone}] 获取验证码成功 → {code}")
            return True, code, False, ""
        else:
            log_warn(f"[{phone}] 验证码接口返回失败: {res}")
            return False, None, False, ""
    except requests.exceptions.ProxyError:
        log_error(f"[{phone}] 验证码接口代理连接异常")
        return None, None, True, ""
    except Exception as e:
        log_error(f"[{phone}] 验证码请求异常: {str(e)}")
        return False, None, True, ""

def register_account(session, phone, pwd, realname, sms_code, invite, proxies):
    url = "http://yun.kenuozn.cn/user/reg"
    headers = {
        "Host": "yun.kenuozn.cn",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://yun.kenuozn.cn",
        "Referer": "http://yun.kenuozn.cn/user/reg/u/1714.html"
    }
    data = {"username": phone, "pwd": pwd, "realname": realname, "phone_code": sms_code, "ref": invite}
    try:
        resp = session.post(url, headers=headers, data=data, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        res = resp.json()
        msg = str(res.get("info", ""))
        # 精准匹配日志里的"手机号已存在"
        if "手机号已存在" in msg or "已注册" in msg or "手机号存在" in msg:
            log_warn(f"[{phone}] 注册接口返回：手机号已存在，放弃此号码")
            return False, False, "registered"
        if res.get("status") == 1:
            log_success(f"[{phone}] 账号注册接口执行成功")
            return True, False, ""
        else:
            log_warn(f"[{phone}] 注册接口返回业务失败: {res}")
            return False, False, ""
    except requests.exceptions.ProxyError:
        log_error(f"[{phone}] 注册接口代理连接异常")
        return None, True, ""
    except Exception as e:
        log_error(f"[{phone}] 注册请求异常: {str(e)}")
        return False, True, ""

def bind_alipay(session, realname, alipay, proxies):
    url = "http://yun.kenuozn.cn/user/info.html"
    headers = {
        "Host": "yun.kenuozn.cn",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"realname": realname, "alipay": alipay, "type": "alipay"}
    try:
        resp = session.post(url, headers=headers, data=data, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        if "修改成功" in resp.text:
            log_success(f"[{alipay}] 支付宝实名绑定完成")
            return True, False
        else:
            log_warn(f"[{alipay}] 实名绑定业务失败")
            return False, False
    except requests.exceptions.ProxyError:
        log_error(f"[{alipay}] 实名接口代理连接异常")
        return None, True
    except Exception as e:
        log_error(f"[{alipay}] 实名绑定请求异常: {str(e)}")
        return False, True

def login(phone, pwd, proxies):
    session = requests.Session()
    url = "http://yun.kenuozn.cn/user/login"
    headers = {
        "Host": "yun.kenuozn.cn",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    data = {"username": phone, "pwd": pwd}
    try:
        resp = session.post(url, headers=headers, data=data, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        res = resp.json()
        if res.get("status") == 1:
            log_success(f"[{phone}] 账号登录校验通过")
            return True, session, False
        else:
            log_warn(f"[{phone}] 登录账号校验失败: {res}")
            return False, None, False
    except requests.exceptions.ProxyError:
        log_error(f"[{phone}] 登录接口代理连接异常")
        return None, None, True
    except Exception as e:
        log_error(f"[{phone}] 登录请求异常: {str(e)}")
        return False, None, True

def sign_task(session, phone, proxies):
    url = "http://yun.kenuozn.cn/user/newsignup"
    headers = {
        "Host": "yun.kenuozn.cn",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36"
    }
    try:
        resp = session.get(url, headers=headers, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        if "签到成功" in resp.text:
            log_success(f"[{phone}] 今日签到执行完成")
            return True, False
        elif "已签到" in resp.text:
            log_info(f"[{phone}] 该账号今日已完成签到，无需重复操作")
            return True, False
        else:
            log_warn(f"[{phone}] 签到接口返回未知响应内容")
            return False, False
    except requests.exceptions.ProxyError:
        log_error(f"[{phone}] 签到接口代理连接异常")
        return None, True
    except Exception as e:
        log_error(f"[{phone}] 签到请求异常: {str(e)}")
        return False, True

def withdraw_task(session, phone, proxies, money="0.1"):
    url = "http://yun.kenuozn.cn/trade/withdraw"
    headers = {
        "Host": "yun.kenuozn.cn",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; 23078RKD5C Build/BP2A.250605.031.A3) AppleWebKit/537.36 Chrome/137.0 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    data = {"money": money, "type": "alipay"}
    try:
        resp = session.post(url, headers=headers, data=data, timeout=REQ_TIMEOUT, proxies=proxies)
        resp.raise_for_status()
        res = resp.json()
        if res.get("status") == 1:
            log_success(f"[{phone}] 提现申请提交成功 → {res['info']}")
            return True, False
        else:
            log_warn(f"[{phone}] 提现业务失败: {res}")
            return False, False
    except requests.exceptions.ProxyError:
        log_error(f"[{phone}] 提现接口代理连接异常")
        return None, True
    except Exception as e:
        log_error(f"[{phone}] 提现请求异常: {str(e)}")
        return False, True

# ===================== 主运行逻辑 =====================
def main():
    main_cfg = os.getenv("KENUOZN_MAIN", "").strip()
    run_mode = os.getenv("KENUOZN_MODE", "").strip().lower()

    if not main_cfg:
        log_error("未配置环境变量 KENUOZN_MAIN，程序终止")
        sys.exit(1)
    if run_mode not in ["reg", "sign"]:
        log_error("KENUOZN_MODE 仅支持 reg / sign，程序终止")
        sys.exit(1)

    cfg_parts = main_cfg.split("#")
    if len(cfg_parts) != 4:
        log_error("KENUOZN_MAIN 格式错误，标准格式：0#占位#邀请码#注册数量")
        sys.exit(1)
    dummy_flag, base_pwd, invite_code, count_str = cfg_parts

    try:
        reg_count = int(count_str)
    except:
        log_error("注册数量必须为纯数字")
        sys.exit(1)
    if reg_count <= 0:
        log_error("注册数量必须大于0")
        sys.exit(1)

    # -------------------------- 注册模式 --------------------------
    if run_mode == "reg":
        log_split("启动注册任务模式")
        log_info(f"目标注册总量：{reg_count} 个账号")
        log_info(f"当前任务邀请码：{invite_code}")
        log_info(f"账号持久化文件：{ACCOUNT_FILE_NAME}")
        total_success = 0
        curr_idx = 0

        while curr_idx < reg_count:
            phone = gen_random_phone()
            pwd = gen_random_password()
            realname = get_random_name()
            alipay = phone
            log_split(f"正在处理待注册号码：{phone}（已成功{total_success}/{reg_count}）")
            skip_this_phone = False
            
            while True:
                current_proxy = get_proxy_ip()
                sess = requests.Session()
                
                sms_ok, sms_code, is_err, flag_sms = get_reg_sms(sess, phone, current_proxy)
                if flag_sms == "registered":
                    skip_this_phone = True
                    break
                if is_err:
                    log_warn("代理异常，换IP重试验证码")
                    continue
                if not sms_ok:
                    log_warn("验证码获取失败，换代理重试")
                    continue

                reg_ok, is_err, flag_reg = register_account(sess, phone, pwd, realname, sms_code, invite_code, current_proxy)
                if flag_reg == "registered":
                    skip_this_phone = True
                    break
                if is_err:
                    log_warn("注册代理异常，重新获取IP")
                    continue
                if not reg_ok:
                    log_warn("注册业务失败，重新获取IP")
                    continue

                bind_ok, is_err = bind_alipay(sess, realname, alipay, current_proxy)
                if is_err:
                    log_warn("实名绑定代理异常，重新获取IP")
                    continue
                if not bind_ok:
                    log_warn("实名绑定失败，重新获取IP")
                    continue

                login_ok, sess_login, is_err = login(phone, pwd, current_proxy)
                if is_err:
                    log_warn("登录代理异常，重新获取IP")
                    continue
                if not login_ok:
                    log_warn("登录校验失败，重新获取IP")
                    continue

                sign_ok, is_err = sign_task(sess_login, phone, current_proxy)
                if is_err:
                    log_warn("签到代理异常，重新获取IP")
                    continue

                withdraw_ok, is_err = withdraw_task(sess_login, phone, current_proxy)
                if is_err:
                    log_warn("提现代理异常，重新获取IP")
                    continue

                append_single_account(phone, pwd, realname, alipay, invite_code)
                total_success += 1
                curr_idx += 1
                break

            if skip_this_phone:
                log_warn(f"========== {phone} 已被注册，自动丢弃，重新生成新手机号 ==========")
                continue

            if curr_idx < reg_count:
                sleep_sec = random.randint(SLEEP_MIN, SLEEP_MAX)
                log_info(f"账号注册完成，休眠 {sleep_sec} 秒后处理下一个新号码")
                time.sleep(sleep_sec)

        log_split("注册任务全部执行完毕 · 汇总")
        log_success(f"本次运行成功注册账号总数：{total_success}")
        log_info(f"所有账号数据已保存至本地 {ACCOUNT_FILE_NAME}")

    # -------------------------- 签到模式 --------------------------
    elif run_mode == "sign":
        log_split("启动登录签到任务模式")
        all_accounts = load_all_accounts()
        if not all_accounts:
            log_warn("本地无任何注册账号，签到任务直接结束")
            sys.exit(0)
        total_acc_num = len(all_accounts)
        log_info(f"读取待签到账号总数量：{total_acc_num} 个")

        for idx, (phone, pwd) in enumerate(all_accounts, 1):
            log_split(f"正在处理第 {idx}/{total_acc_num} 个签到账号")
            log_info(f"目标签到手机号：{phone}")

            while True:
                proxy = get_proxy_ip()
                login_ok, sess_login, is_err = login(phone, pwd, proxy)
                if is_err:
                    log_warn("登录代理异常，重新获取IP")
                    continue
                if not login_ok:
                    log_warn("账号登录失败，重新获取IP")
                    continue

                sign_ok, is_err = sign_task(sess_login, phone, proxy)
                if is_err:
                    log_warn("签到代理异常，重新获取IP")
                    continue
                break

            delay_sec = random.randint(SIGN_DELAY_MIN, SIGN_DELAY_MAX)
            log_info(f"当前账号签到完成，延时 {delay_sec} 秒后处理下一个账号")
            time.sleep(delay_sec)

        log_split("签到任务全部执行完毕 · 汇总")
        log_success(f"全部 {total_acc_num} 个账号已完成签到处理（成功/已签到）")

if __name__ == "__main__":
    main()