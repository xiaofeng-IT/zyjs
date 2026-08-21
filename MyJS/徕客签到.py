import time, json, sys, random, argparse, base64, os, logging, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import requests
except ImportError:
    print("[-] 缺少 requests 库，请安装：pip install requests")
    sys.exit(1)

# ====================================================================
# 配置区（默认值，运行时从环境变量读取）
# ====================================================================
API_BASE_URL = "https://www.ljgglp.com/api.php"           # 接口地址
PROXY_API = os.environ.get("PROXY_API", "")  # 代理 API 地址（每次请求获取新IP，与 PROXY 二选一）
PROXY = os.environ.get("PROXY", "")  # 固定代理地址（所有账号共用一个IP，与 PROXY_API 二选一）
WATCH_TIMES = int(os.environ.get("WATCH_TIMES", "10"))  # 每次运行最多看几次广告
WATCH_WAIT_SEC = os.environ.get("WATCH_WAIT_SEC", "30-35")  # 观看广告等待秒数，支持范围格式如 "30-35"
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))  # 网络请求最大重试次数
RETRY_DELAY_SEC = int(os.environ.get("RETRY_DELAY_SEC", "3"))  # 重试间隔时间（秒）
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "5"))  # 最大线程数（并发执行的账号数）
REQUEST_TIMEOUT = 20  # 请求超时时间（秒）
MIN_DELAY = 1  # 步骤间最小延迟秒数（随机延迟下限）
MAX_DELAY = 3  # 步骤间最大延迟秒数（随机延迟上限）


logging.basicConfig(
    level=getattr(logging, os.environ.get("PYTHON_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [Thread-%(thread)d] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ljgglp")


print_lock = threading.Lock()

REFERER = "https://www.ljgglp.com"

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 14; SM-S9280) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
)


class LjgglpError(Exception):
    pass


def get_proxy() -> dict:
    if PROXY:
        return {"http": PROXY, "https": PROXY}
    if PROXY_API:
        for _ in range(3):
            try:
                r = requests.get(PROXY_API, timeout=10)
                text = r.text.strip()
                if ":" in text:
                    p = "http://" + text
                    log.debug("获取到新代理: %s", p)
                    return {"http": p, "https": p}
            except Exception as e:
                log.warning("获取代理失败: %s", e)
                time.sleep(1)
    return {}


def random_delay(min_sec: float = None, max_sec: float = None, reason: str = ""):
    min_sec = min_sec if min_sec is not None else MIN_DELAY
    max_sec = max_sec if max_sec is not None else MAX_DELAY
    delay = random.uniform(min_sec, max_sec)
    tag = f" ({reason})" if reason else ""
    log.info("等待 %.1f 秒...%s", delay, tag)
    time.sleep(delay)


def decode_jwt_payload(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except Exception:
        return {}


def format_time(ts):
    if not ts:
        return "未知"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))


def token_seconds_left(token):
    payload = decode_jwt_payload(token)
    exp_time = payload.get("exp_time")
    if not exp_time:
        return None
    return int(exp_time) - int(time.time())


def is_token_expired(token):
    seconds_left = token_seconds_left(token)
    return seconds_left is not None and seconds_left <= 0


def ensure_token_available(token):
    if not token:
        raise LjgglpError("未填写 JWT_TOKEN")
    payload = decode_jwt_payload(token)
    if not payload:
        raise LjgglpError("JWT_TOKEN 格式异常，无法解析")
    exp_time = payload.get("exp_time")
    if exp_time and int(exp_time) <= int(time.time()):
        raise LjgglpError("平台 token 已过期，需要重新登录获取新 token")
    return payload


def print_token_info(token, payload=None):
    if not token:
        print("[-] 未填写 JWT_TOKEN")
        return False
    payload = payload or decode_jwt_payload(token)
    if not payload:
        print("[-] JWT_TOKEN 格式异常，无法解析")
        return False
    exp_time = payload.get("exp_time")
    seconds_left = token_seconds_left(token)
    print("=" * 40)
    print("  Token 信息")
    print("=" * 40)
    print("  uid: {0}".format(payload.get("uid", "未知")))
    print("  deviceId: {0}".format(payload.get("deviceId", "未知")))
    print("  unionid: {0}".format(payload.get("unionid", "未知")))
    print("  过期时间: {0}".format(format_time(exp_time)))
    if seconds_left is None:
        print("  剩余时间: 未知")
    elif seconds_left <= 0:
        print("  状态: 已过期，需要重新登录")
    else:
        days = seconds_left // 86400
        hours = (seconds_left % 86400) // 3600
        minutes = (seconds_left % 3600) // 60
        print("  剩余时间: {0}天 {1}小时 {2}分钟".format(days, hours, minutes))
        print("  状态: 有效")
    return seconds_left is None or seconds_left > 0


class LjgglpClient:
    def __init__(self, verbose=False, session=None):
        self.verbose = verbose
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": REFERER,
        })
        self.device_id = None
        self.user_token = None
        self.uid = None

    def _log(self, msg, level="info"):
        prefix = {"info": "[*]", "ok": "[+]", "err": "[-]", "dbg": "[D]"}.get(level, "[*]")
        with print_lock:
            log.info("{0} {1}".format(prefix, msg))

    def _dbg(self, msg):
        if self.verbose:
            self._log(msg, "dbg")

    def _gen_device_id(self):
        ts = str(int(time.time() * 1000))
        suffix = str(random.randint(100000, 9999999))
        return ts + suffix


    def _request(self, method, endpoint, params=None, data=None):
        url = "{0}/{1}".format(API_BASE_URL, endpoint)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method.upper() == "GET":
                    resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                else:
                    resp = self.session.post(url, data=data, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                msg = "请求超时 ({0}/{1})".format(attempt, MAX_RETRIES)
                with print_lock:
                    log.error(msg) if attempt == MAX_RETRIES else log.debug(msg)
            except requests.exceptions.ConnectionError as e:
                msg = "网络连接失败 ({0}/{1}): {2}".format(attempt, MAX_RETRIES, str(e))
                with print_lock:
                    log.error(msg) if attempt == MAX_RETRIES else log.debug(msg)
                if attempt < MAX_RETRIES and (PROXY_API or PROXY):
                    new_proxy = get_proxy()
                    if new_proxy:
                        self.session.proxies.update(new_proxy)
                        with print_lock:
                            log.info("切换代理至: %s", new_proxy.get('http', ''))
            except requests.exceptions.HTTPError as e:
                raise LjgglpError("HTTP错误: {0}".format(e))
            except json.JSONDecodeError:
                raise LjgglpError("响应格式异常")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
        raise LjgglpError("请求失败 (已重试{0}次)".format(MAX_RETRIES))

    def _post_auth(self, endpoint, **extra):
        if not all([self.user_token, self.uid, self.device_id]):
            raise LjgglpError("未登录")
        data = {"deviceId": self.device_id,
                "userToken": self.user_token,
                "uid": self.uid}
        data.update(extra)
        if self.verbose:
            dbg = {k: (v[:30]+"..." if isinstance(v,str) and len(v)>30 else v) for k,v in data.items()}
            self._dbg("POST {0} data={1}".format(endpoint, dbg))
        result = self._request("POST", endpoint, data=data)
        if result.get("status") == 2 and "登录失效" in result.get("info",""):
            self._log("登录已失效(token过期)，请重新login", "err")
            raise LjgglpError("token过期")
        return result

    def login_with_account(self, phone, password):
        if not phone or not password:
            raise LjgglpError("手机号和密码不能为空")
        self.device_id = self._gen_device_id()
        masked_phone = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else "***"
        with print_lock:
            log.info("正在登录... 手机号={0} deviceId={1}".format(masked_phone, self.device_id))
        data = {"phone": phone, "password": password, "deviceId": self.device_id}
        result = self._request("POST", "Login/accountLogin", data=data)
        if result.get("status") != 1:
            raise LjgglpError("登录失败：{0}".format(result.get("info", "未知错误")))
        self.user_token = result["data"]["token"]
        self.uid = result["data"]["uid"]
        with print_lock:
            log.info("登录成功！用户ID: {0}".format(self.uid))
            log.info("新的 JWT_TOKEN: {0}".format(self.user_token))
            log.info("新的 DEVICE_ID: {0}".format(self.device_id))
        return True

    def login_with_token(self, token, uid=None, device_id=None):
        payload = ensure_token_available(token)
        print_token_info(token, payload)
        token_uid = payload.get("uid")
        token_device_id = payload.get("deviceId")
        if token_uid and uid and str(uid) != str(token_uid):
            with print_lock:
                log.error("USER_ID 与 token 内 uid 不一致，已优先使用 token 内 uid: {0}".format(token_uid))
        uid = token_uid or uid
        device_id = token_device_id or device_id or self._gen_device_id()
        if not uid:
            raise LjgglpError("缺少 USER_ID，且无法从 JWT_TOKEN 解析 uid")
        self.user_token = token
        self.uid = uid
        self.device_id = device_id
        with print_lock:
            log.info("Token已设置，用户ID: {0}".format(self.uid))
        self._dbg("deviceId={0}".format(self.device_id))
        return True

    def get_user_info(self):
        result = self._post_auth("User/getUserInfo")
        return result.get("data", {})

    def show_user_info(self):
        try:
            info = self.get_user_info()
        except LjgglpError as e:
            with print_lock:
                log.error(str(e))
            return
        with print_lock:
            print()
            print("=" * 40)
            print("  用户信息")
            print("=" * 40)
            print("  昵称: {0}".format(info.get("userName") or info.get("lg_user_name") or "未设置"))
            print("  手机: {0}".format(info.get("lg_user_phone") or info.get("userPhone") or "未绑定"))
            print("  乐豆: {0}".format(info.get("ld_number", "0")))
            print("  用户ID: {0}".format(info.get("uid", self.uid)))
            print("  设备ID: {0}".format(info.get("deviceId", self.device_id)))
            if info.get("unionid"):
                print("  unionid: {0}".format(info["unionid"]))
            if info.get("app_openid"):
                print("  app_openid: {0}".format(info["app_openid"]))
            if info.get("xcx_openid"):
                print("  xcx_openid: {0}".format(info["xcx_openid"]))
            print()
        try:
            ad = self.check_ad_info()
            if ad and isinstance(ad, dict) and ad.get("ld_number") is not None:
                print("  广告乐豆: {0}(今日已看 {1}/{2})".format(
                    ad["ld_number"], ad.get("todayCount",0), ad.get("maxCount",0)))
        except LjgglpError:
            pass
        print()

    def check_ad_info(self):
        result = self._post_auth("Lg/adWatchInfo")
        data = result.get("data", {})
        return data if isinstance(data, dict) else None
    def ad_watch_flow(self, count=10, wait_range="15"):
        try:
            if "-" in wait_range:
                parts = wait_range.split("-")
                wait_min, wait_max = int(parts[0]), int(parts[1])
            else:
                wait_min = wait_max = int(wait_range)
        except:
            with print_lock:
                log.error("等待时间参数格式错误，使用默认 12-18")
            wait_min, wait_max = 12, 18
        if wait_min < 5:
            wait_min = 5
        if wait_max < wait_min:
            wait_max = wait_min
        with print_lock:
            log.info("查询广告观看信息...")
        ad = self.check_ad_info()
        if not ad:
            with print_lock:
                log.error("无法获取广告信息")
            return 0
        can_watch = int(ad.get("canWatch", 0))
        today = int(ad.get("todayCount", 0))
        max_count = int(ad.get("maxCount", 10))
        ld_balance = ad.get("ld_number", "0")
        with print_lock:
            log.info("今日已看: {0}/{1}次 | 当前乐豆: {2} | 可看: {3}".format(
                today, max_count, ld_balance, "是" if can_watch else "否"))
        if not can_watch:
            with print_lock:
                log.error("今日广告次数已用完")
            return 0
        remaining = max_count - today
        if count > remaining:
            count = remaining
            with print_lock:
                log.info("最多还能看 {0} 次".format(count))
        total_reward = 0.0
        success_count = 0
        for i in range(1, count + 1):
            with print_lock:
                print()
                log.info("第 {0}/{1} 次 ---".format(i, count))
            try:
                ad = self.check_ad_info()
                if not ad or not ad.get("canWatch", 0):
                    with print_lock:
                        log.error("广告配额已用完，结束")
                    break
            except LjgglpError as e:
                if "token" in str(e): break
                continue
            try:
                result = self._post_auth("Lg/adWatchStart")
                play_token = result["data"].get("playToken", "")
            except LjgglpError as e:
                if "token" in str(e): break
                with print_lock:
                    log.error("获取播放令牌失败: {0}".format(e))
                continue
            if not play_token:
                with print_lock:
                    log.error("播放令牌为空")
                continue
            with print_lock:
                log.info("获取 playToken: {0}".format(play_token))
            wait_time = random.randint(wait_min, wait_max)
            with print_lock:
                log.info("模拟观看广告，等待 {0} 秒...".format(wait_time))
            for _ in range(wait_time):
                time.sleep(1)
            with print_lock:
                print()
            try:
                result = self._post_auth("Lg/adWatchCallback", playToken=play_token)
                reward = float(result.get("data",{}).get("reward", 0))
                total_reward += reward
                success_count += 1
                with print_lock:
                    log.info("领取成功！+{0:.2f} 乐豆，共 {1:.2f}".format(reward, total_reward))
            except LjgglpError as e:
                if "token" in str(e): break
                with print_lock:
                    log.error("领取失败: {0}".format(e))
                continue
        with print_lock:
            print()
            print("=" * 40)
            log.info("完成！成功 {0}/{1} 次，共获得 {2:.2f} 乐豆".format(
                success_count, count, total_reward))
        return total_reward




def parse_accounts():
    accounts_str = os.environ.get("lk", "")
    if not accounts_str:
        with print_lock:
            log.error("未找到环境变量 lk，请在青龙面板中设置")
            log.error("格式: 手机号#密码&手机号#密码")
        return []

    accounts = []
    for account in accounts_str.split("&"):
        account = account.strip()
        if not account:
            continue
        parts = account.split("#")
        if len(parts) == 2:
            phone, password = parts[0].strip(), parts[1].strip()
            if phone and password:
                accounts.append((phone, password))
            else:
                with print_lock:
                    log.warning("跳过无效账号: %s", account)
        else:
            with print_lock:
                log.warning("账号格式错误: %s (应为 手机号#密码)", account)

    if accounts:
        with print_lock:
            log.info("成功解析 %d 个账号", len(accounts))
    else:
        with print_lock:
            log.error("未解析到有效账号")

    return accounts




def run_single_account(phone: str, password: str) -> bool:
    with print_lock:
        log.info("=" * 60)
        log.info("开始处理账号: %s", phone)
        log.info("=" * 60)

    session = requests.Session()
    proxy_dict = get_proxy()
    if proxy_dict:
        session.proxies.update(proxy_dict)
        with print_lock:
            log.info("使用代理: %s", proxy_dict.get("http", ""))
    else:
        with print_lock:
            log.info("直连模式")

    client = LjgglpClient(verbose=False, session=session)

    try:
        with print_lock:
            log.info("=== 步骤1: 登录 ===")
        login_success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client.login_with_account(phone, password)
                login_success = True
                break
            except LjgglpError as e:
                with print_lock:
                    log.warning("登录失败，第%d次重试... %s", attempt, str(e))
                random_delay(reason="登录重试等待")
        
        if not login_success:
            with print_lock:
                log.error("❌ 账号 %s 登录失败，已耗尽重试次数", phone)
            return False

        random_delay(reason="登录后等待")

        with print_lock:
            log.info("=== 步骤2: 看广告领乐豆 ===")
        client.ad_watch_flow(count=WATCH_TIMES, wait_range=WATCH_WAIT_SEC)

        with print_lock:
            log.info("✅ 账号 %s 处理完成", phone)
            log.info("=" * 60)
        return True

    except Exception as e:
        with print_lock:
            log.error("❌ 账号 %s 处理异常: %s", phone, str(e))
        return False




def main():
    with print_lock:
        log.info("🚀 徕客签到脚本启动（青龙面板多线程版）")
        log.info("脚本版本: 青龙面板版 - 多线程")
        log.info("最大并发线程数: %d", MAX_WORKERS)

    accounts = parse_accounts()
    if not accounts:
        with print_lock:
            log.error("❌ 没有可用账号，退出")
        return

    success_count = 0
    fail_count = 0

    with print_lock:
        log.info("\n🚀 开始并发处理 %d 个账号...", len(accounts))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="AccountWorker") as executor:
        future_to_account = {
            executor.submit(run_single_account, phone, password): (idx, phone)
            for idx, (phone, password) in enumerate(accounts, 1)
        }

        for future in as_completed(future_to_account):
            idx, phone = future_to_account[future]
            try:
                result = future.result()
                if result:
                    success_count += 1
                    with print_lock:
                        log.info("✅ 第 %d 个账号 %s 处理成功", idx, phone)
                else:
                    fail_count += 1
                    with print_lock:
                        log.error("❌ 第 %d 个账号 %s 处理失败", idx, phone)
            except Exception as e:
                fail_count += 1
                with print_lock:
                    log.error("❌ 第 %d 个账号 %s 处理异常: %s", idx, phone, e)

    with print_lock:
        log.info("\n" + "=" * 60)
        log.info("📊 执行总结")
        log.info("总账号数: %d", len(accounts))
        log.info("成功: %d", success_count)
        log.info("失败: %d", fail_count)
        log.info("=" * 60)
        log.info("🎉 全部完成")


if __name__ == "__main__":
    main()
