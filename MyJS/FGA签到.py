# -*- coding: utf-8 -*-
import requests, json, os, sys, random, logging, time, uuid, base64, urllib3
import ddddocr

urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)
''' qq项目群764401583群内软件免费使用
    qq项目群764401583群内软件免费使用
    qq项目群764401583群内软件免费使用'''

# ======================== 用户配置区 ========================
''' qq项目群764401583群内软件免费使用
    qq项目群764401583群内软件免费使用
    qq项目群764401583群内软件免费使用'''

BASE_URL = "http://211.154.19.66:8080"
PROXY_API = ""
PROXY = ""
QINGLONG_ENV_VAR = "fga"              # 青龙面板环境变量名
DEFAULT_PASSWORD = "qwe12345"
DEVICE_MODEL = "PHM110"
CAPTCHA_MAX_RETRY = 5
REQUEST_TIMEOUT = 15
MIN_DELAY = 1
MAX_DELAY = 3


# ======================== 全局对象 ========================

ocr = ddddocr.DdddOcr(show_ad=False)


def random_delay(min_sec=None, max_sec=None, reason=""):
    min_sec = min_sec or MIN_DELAY
    max_sec = max_sec or MAX_DELAY
    delay = random.uniform(min_sec, max_sec)
    tag = " (%s)" % reason if reason else ""
    log.info("等待 %.1f 秒...%s", delay, tag)
    time.sleep(delay)


def get_proxy():
    if PROXY:
        return {"http": PROXY, "https": PROXY}
    if PROXY_API:
        for _ in range(3):
            try:
                r = requests.get(PROXY_API, timeout=10)
                text = r.text.strip()
                if ":" in text:
                    p = "http://" + text
                    return {"http": p, "https": p}
            except:
                time.sleep(1)
    return None


def build_headers(token=None, content_type=None):
    headers = {
        "Host": "211.154.19.66:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; PHM110 Build/QKQ1.191014.001; wv) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "X-Requested-With": "uni-app",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "http://211.154.19.66:8080/",
    }
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["authorization"] = token
    return headers


def make_session():
    s = requests.Session()
    proxy_dict = get_proxy()
    if proxy_dict:
        s.proxies.update(proxy_dict)
        log.info("使用代理: %s", proxy_dict.get("http", ""))
    else:
        log.info("直连模式")
    return s


def api_get(session, path, params=None, token=None):
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    headers = build_headers(token=token)
    headers.pop("Content-Type", None)
    for _ in range(3):
        try:
            r = session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT, verify=False)
            r.encoding = "utf-8"
            return r
        except requests.exceptions.RequestException as e:
            log.warning("GET请求失败: %s, 重试...", e)
            random_delay(1, 2, "请求重试")
    return None


def api_post(session, path, data=None, token=None):
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    headers = build_headers(token=token, content_type="application/json;charset=UTF-8")
    for _ in range(3):
        try:
            r = session.post(url, headers=headers, json=data or {}, timeout=REQUEST_TIMEOUT, verify=False)
            r.encoding = "utf-8"
            return r
        except requests.exceptions.RequestException as e:
            log.warning("POST请求失败: %s, 重试...", e)
            random_delay(1, 2, "请求重试")
    return None


# ======================== 步骤函数 ========================

def step_captcha(session):
    """获取图片验证码, 返回 (uuid, code) 或 (None, None)"""
    for attempt in range(1, CAPTCHA_MAX_RETRY + 1):
        uid = uuid.uuid4().hex.replace("-", "")
        log.info("获取验证码 (第%d次), uuid=%s", attempt, uid[:16])
        r = api_get(session, "/v1/common/captcha/fga-image", params={"uuid": uid})
        if r is None or r.status_code != 200:
            log.warning("验证码请求失败")
            random_delay(1, 2, "重试验证码")
            continue
        try:
            data = r.json()
        except:
            log.warning("验证码响应非JSON")
            continue
        img_b64 = data.get("img", "")
        if not img_b64:
            log.warning("验证码响应无img字段")
            continue
        try:
            img_bytes = base64.b64decode(img_b64)
            uid = data.get("uuid", uid)
            code = ocr.classification(img_bytes)
        except:
            log.warning("验证码base64解码失败")
            continue
        code = code.strip().lower()
        log.info("验证码识别结果: %s", code)
        if code and len(code) >= 3:
            return uid, code
        log.warning("验证码识别不完整: %s", code)
        random_delay(1, 2, "重试验证码")
    log.error("验证码获取失败，已耗尽重试次数")
    return None, None


def step_login(session, username, password, captcha_uuid, captcha_code):
    """登录, 返回响应dict或None"""
    payload = {
        "username": username,
        "password": password,
        "googleCode": "",
        "deviceId": uuid.uuid4().hex.replace("-", "")[:16],
        "deviceModel": DEVICE_MODEL,
        "code": captcha_code,
        "uuid": captcha_uuid,
    }
    log.info("登录: %s", username)
    r = api_post(session, "/v1/login", data=payload)
    if r is None:
        return None
    try:
        data = r.json()
    except:
        log.error("登录响应非JSON: %s", r.text[:200])
        return None
    if data.get("code") == 200:
        log.info("登录成功, uid=%s", data.get("data", {}).get("uid", "?"))
        return data
    log.warning("登录失败: %s | 完整响应: %s", data.get("msg", "?"), json.dumps(data, ensure_ascii=False))
    return data


def step_user_info(session, token):
    """获取用户信息"""
    r = api_get(session, "/v1/user/info", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        log.error("用户信息响应非JSON")
        return None


def step_account_list(session, token):
    """获取资产列表"""
    r = api_get(session, "/v1/account/list", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


def step_mining_list(session, token):
    """获取矿机列表"""
    r = api_get(session, "/v1/miningmachine/getMiningList", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


def step_mining_upgrade_configs(session, token):
    """获取升级配置"""
    r = api_get(session, "/v1/miningmachine/getUpgradeConfigs", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


def step_start_machine(session, token, machine_id):
    """启动矿机"""
    log.info("启动矿机: id=%s", machine_id)
    r = api_get(session, "/v1/miningmachine/startMachine/%s" % machine_id, token=token)
    if r is None:
        return None
    try:
        data = r.json()
        if data.get("code") == 200:
            log.info("矿机 %s 启动成功", machine_id)
        else:
            log.warning("矿机启动失败: %s", data.get("msg", r.text[:200]))
        return data
    except:
        log.error("矿机启动响应非JSON: %s", r.text[:200])
        return None


def step_signin_detail(session, token):
    """签到详情"""
    r = api_get(session, "/v1/signin/detail", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


def step_signin(session, token):
    """签到"""
    log.info("执行签到")
    r = api_post(session, "/v1/signin", data={}, token=token)
    if r is None:
        return None
    try:
        data = r.json()
        if data.get("code") == 200:
            d = data.get("data", {})
            log.info("签到成功: 第%d天, +%.0f积分", d.get("dayIndex", "?"), d.get("pointsReward", 0))
        else:
            log.warning("签到失败: %s", data.get("msg", ""))
        return data
    except:
        return None


def step_mining_assist_balance(session, token):
    """获取助力余额"""
    r = api_get(session, "/v1/mining/assist/balance", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


def step_mining_assist_draw(session, token):
    """抽取助力卡"""
    log.info("抽取助力卡")
    r = api_post(session, "/v1/mining/assist/draw", data={}, token=token)
    if r is None:
        return None
    try:
        data = r.json()
        if data.get("code") == 200:
            card = data.get("data", {}).get("card", {})
            if card:
                log.info("抽卡成功: %s (%s)", card.get("cardName", "?"), card.get("cardNo", "?"))
            else:
                log.info("助力次数已用完")
        else:
            log.warning("抽卡失败: %s", data.get("msg", ""))
        return data
    except:
        return None


def step_computing_power(session, token):
    """查算力余额"""
    r = api_get(session, "/v1/computing-power/balance", token=token)
    if r is None:
        return None
    try:
        return r.json()
    except:
        return None


# ======================== 账号文件操作 ========================

def load_accounts(filepath):
    """加载账号文件, 每行: 手机号----密码"""
    if not filepath or not os.path.exists(filepath):
        return []
    accounts = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "----" in line:
                parts = line.split("----", 1)
                phone = parts[0].strip()
                pwd = parts[1].strip() if len(parts) > 1 else ""
                if phone:
                    accounts.append({"phone": phone, "password": pwd or DEFAULT_PASSWORD})
            elif line:
                accounts.append({"phone": line, "password": DEFAULT_PASSWORD})
    return accounts



# ======================== 主流程 ========================

def run_single(session, token):
    """使用已有token执行完整操作流程"""
    log.info("=" * 40)
    log.info("开始执行操作")
    log.info("=" * 40)

    # 1. 用户信息
    random_delay(reason="获取用户信息")
    info = step_user_info(session, token)
    if info and info.get("code") == 200:
        user = info.get("data", {})
        log.info("用户: %s (UID=%s, 邀请码=%s)", user.get("mobile", "?"), user.get("id", "?"), user.get("inviteCode", "?"))

    # 2. 资产
    random_delay(reason="获取资产")
    acc = step_account_list(session, token)
    if acc and acc.get("code") == 200:
        total = acc.get("data", {}).get("totalUsdAmount", 0)
        log.info("总资产: $%.6f USD", total)
        for coin in acc.get("data", {}).get("list", []):
            n = coin.get("normalBalance", 0)
            f = coin.get("frozenBalance", 0)
            lk = coin.get("lockBalance", 0)
            if n or f or lk:
                log.info("  %s: 可用=%s 冻结=%s 锁仓=%s 估值$%s", coin.get("symbol","?"), n, f, lk, coin.get("priceLockUsd",0))

    # 3. 矿机列表 + 启动
    random_delay(reason="查询矿机")
    mining = step_mining_list(session, token)
    if mining is None:
        log.error("矿机列表查询失败")
        return False
    if mining.get("code") != 200:
        log.error("矿机列表异常: %s", mining.get("msg", ""))
        return False

    md = mining.get("data", {})
    log.info("矿机等级: %s, 已邀请: %d人", md.get("level", "?"), md.get("userInviteCount", 0))
    log.info("当前挖矿收益: %.6f FGA", md.get("currentMiningEarnings", 0))

    machines = md.get("userMachines", [])
    if not machines:
        log.warning("没有矿机")
    else:
        for m in machines:
            mid = m.get("id")
            status = m.get("status", "?")
            last_start = m.get("lastStartTime", 0)
            status_str = "已启动" if status == 0 else "已停止" if status == 1 else "未知"
            log.info("矿机 #%s: type=%s, status=%s, start=%s", mid, m.get("machineType","?"), status_str, m.get("startTime","?"))
            if status == 1 or last_start == 0:
                random_delay(reason="准备启动矿机")
                step_start_machine(session, token, mid)
            else:
                log.info("矿机 #%s 已在运行中", mid)

    # 4. 升级配置
    random_delay(reason="查询升级配置")
    upgrade = step_mining_upgrade_configs(session, token)
    if upgrade and upgrade.get("code") == 200:
        configs = upgrade.get("data", [])
        log.info("矿机升级配置 (%d种):", len(configs))
        for cfg in configs:
            log.info("  Type%s: 日产%.1f FGA  需邀请%d人  需锁仓%.0f FGA  一键$%.1f",
                     cfg.get("machineType","?"), cfg.get("normalUserDailyToken",0),
                     cfg.get("requiredInvite",0), cfg.get("requiredToken",0), cfg.get("oneClickPrice",0))

    # 5. 签到
    random_delay(reason="查询签到")
    sd = step_signin_detail(session, token)
    if sd and sd.get("code") == 200:
        d = sd.get("data", {})
        if d.get("isSignin"):
            log.info("今日已签到 (连续%d天, %d分)", d.get("continuousDays", 0), int(d.get("availablePoints", 0)))
        else:
            log.info("今日未签到 (连续%d天, %d分)", d.get("continuousDays", 0), int(d.get("availablePoints", 0)))
            random_delay(reason="执行签到")
            step_signin(session, token)

    # 6. 算力余额
    random_delay(reason="查询算力")
    cp = step_computing_power(session, token)
    if cp and cp.get("code") == 200:
        cpd = cp.get("data", {})
        log.info("算力: 总计=%d 已用=%d 剩余=%d", int(cpd.get("totalEarned",0)), int(cpd.get("totalSpent",0)), int(cpd.get("balance",0)))

    # 7. 助力卡抽取
    random_delay(reason="查询助力次数")
    ab = step_mining_assist_balance(session, token)
    if ab and ab.get("code") == 200:
        available = ab.get("data", {}).get("availableCount", 0)
        log.info("助力卡余量: %d 次", available)
        while available > 0:
            random_delay(reason="抽取助力卡")
            draw = step_mining_assist_draw(session, token)
            if draw is None or draw.get("code") != 200:
                break
            available = draw.get("data", {}).get("availableCount", 0)
            log.info("剩余助力次数: %d", available)
            random_delay(1, 2)

    log.info("=" * 40)
    log.info("全流程执行完毕")
    log.info("=" * 40)
    return True


def run_by_phone(phone, password):
    """手机号+密码登录后执行操作"""
    session = make_session()

    captcha_uuid, captcha_code = step_captcha(session)
    if not captcha_uuid:
        log.error("验证码获取失败，跳过 %s", phone)
        return False

    login_data = step_login(session, phone, password, captcha_uuid, captcha_code)
    if login_data is None:
        log.error("登录失败（网络错误），跳过 %s", phone)
        return False
    if login_data.get("code") != 200:
        log.error("登录失败: %s", login_data.get("msg", ""))
        return False

    token = login_data.get("data", {}).get("token", "")
    if not token:
        log.error("登录响应无token")
        return False

    log.info("获取到token: %s...", token[:40])
    return run_single(session, token)


def parse_qinglong_accounts():
    """从青龙面板环境变量解析账号列表
    
    格式: 手机号#密码&手机号#密码
    返回: [{"phone": xxx, "password": xxx}, ...]
    """
    env_value = os.environ.get(QINGLONG_ENV_VAR, "")
    if not env_value:
        log.error("未找到环境变量 %s，请检查青龙面板配置", QINGLONG_ENV_VAR)
        return []
    
    accounts = []
    account_pairs = env_value.split("&")
    for pair in account_pairs:
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split("#")
        if len(parts) == 2:
            phone, password = parts[0].strip(), parts[1].strip()
            if phone:
                pwd = password if password else DEFAULT_PASSWORD
                accounts.append({"phone": phone, "password": pwd})
                log.info("解析账号: %s", phone)
        else:
            log.warning("账号格式错误，跳过: %s", pair)
    
    if not accounts:
        log.error("未解析到有效账号，请检查环境变量格式")
    
    log.info("共解析 %d 个账号", len(accounts))
    return accounts


def main():
    """主入口 - 仅支持青龙面板运行"""
    log.info("qq项目群764401583群内软件免费使用")
    log.info("FGA 自动化脚本启动")
    log.info("=" * 60)
    log.info("青龙面板环境变量配置说明:")
    log.info("  变量名: %s", QINGLONG_ENV_VAR)
    log.info("  单账号格式: 手机号#密码")
    log.info("  多账号格式: 手机号#密码&手机号#密码")
    log.info("  示例: 13800138000#abc123&13900138000#def456")
    log.info("  注意: 密码留空则使用默认密码 %s", DEFAULT_PASSWORD)
    log.info("=" * 60)
    log.info("代理: %s", "直连" if not (PROXY or PROXY_API) else (PROXY or "API代理"))
    
    # 从环境变量读取多账号
    accounts = parse_qinglong_accounts()
    
    if not accounts:
        log.error("没有可用账号，程序退出")

        return
    
    success_count = 0
    fail_count = 0
    
    for idx, acc in enumerate(accounts, 1):
        log.info("\n" + "=" * 60)
        log.info("处理第 %d/%d 个账号: %s", idx, len(accounts), acc["phone"])
        log.info("=" * 60)
        
        try:
            ok = run_by_phone(acc["phone"], acc["password"])
            if ok:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            log.error("账号 %s 执行异常: %s", acc["phone"], e)
            import traceback
            traceback.print_exc()
            fail_count += 1
        
        # 账号间延迟
        if idx < len(accounts):
            delay = random.uniform(3, 8)
            log.info("\n等待 %.1f 秒后处理下一个账号...", delay)
            time.sleep(delay)
    
    log.info("\n" + "=" * 60)
    log.info("所有账号处理完成！成功: %d, 失败: %d", success_count, fail_count)
    log.info("=" * 60)
    


if __name__ == "__main__":
    main()

