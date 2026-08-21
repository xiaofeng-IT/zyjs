#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 账号环境变量 qwdj：备注#Bearer令牌#app令牌（分隔符 & 或换行均可）
#   第2段 = 登录机产出的 "Bearer eyJ..."（刷币用，24h过期）
#   第3段 = app令牌（可选，登录机第3段）；填了就能在 Bearer 过期时自动换新，无需重登
# 代理环境变量 qwdj_proxy（可选）：代理提取API链接(如 IPzan core-extract)，每账号自动取一个IP，失败自动换
import os
import re
import time
import json
import uuid
import base64
import random
import hashlib
import requests
import threading

# 禁用请求警告
requests.packages.urllib3.disable_warnings()

# 固定配置
SIGN_KEY = "nEs^sksaDvFJE8@#H!Stj7&1pMGvrBCc"
APP_ID = "app006"
PKG = os.getenv("qwdj_pkg", "com.leguo.life")     # X-Requested-With 包名（黔微短剧=com.leguo.life）
H5_ORIGIN = "https://sdk-h5.xjdy2024.com"          # H5 接口 Origin
FIXED_DURATION = 60004
AD_POINTS_RANGE = (200000, 500000)
EXCHANGE_INTERVAL = 1  # 兑换间隔10秒
MAX_LOOP = 999          # 最大循环次数
# 金币上限：今日金币(today_coins) ≥ 此值就停掉该账号所有任务；可用环境变量 qwdj_coin_cap 覆盖
COIN_CAP = int(os.getenv("qwdj_coin_cap", "3000000") or "3000000")
# 广告上报默认关闭：b_id 被穿山甲 S2S 校验，随机 UUID 一律 50701"广告标识无效,疑似刷量"，
# 会触发风控甚至封号。纯 HTTP 无法伪造有效广告标识。确需开启设 qwdj_ad=1（不推荐）。
AD_REPORT_ENABLED = os.getenv("qwdj_ad", "0").strip() == "1"

# 接口地址
URLS = {
    "video_report": "https://sdk.xjdy2024.com/api/user/watch-duration/report",
    "ad_report": "https://sdk.xjdy2024.com/api/user/report-points",
    "exchange": "https://sdk.xjdy2024.com/api/user/exchange-coins",
    "my_stats": "https://sdk.xjdy2024.com/api/user/my-stats",   # 金币/积分余额
    "treasure": "https://sdk.xjdy2024.com/api/activity/progress?activity_code=cooldown_treasure_box&action=claim",
    "red_envelope": "https://sdk.xjdy2024.com/api/activity/progress?activity_code=red_envelope_rain&action=claim"
}

# 提现功能已拆分到独立脚本「黔微提现本.py」，本脚本只负责刷币，不再自动提现。

# ---------------- Bearer 自动刷新（app令牌 → 新24h Bearer，无需重登）----------------
# 逆向验证：刷币 Bearer(adtask-sdk JWT)=24h过期；用第3段 app令牌走
#   userInfo → PKCE → xjsdk/auth(拿authCode) → user/sync 即可换新，且不绑 deviceId。
APP_API = "http://app.gzqianwei.cn/api"                     # app令牌所属服务（换新用）
SDK_SYNC_URL = "https://sdk.xjdy2024.com/api/user/sync"     # authCode → 新JWT
SDK_SYNC_UA = "Dalvik/2.1.0 (Linux; U; Android 14; 22041211AC Build/UP1A.231005.007)"
# Bearer 剩余有效期低于该秒数(默认30分钟)就提前刷新；设 0 只在过期后刷新
REFRESH_SKEW = int(float(os.getenv("qwdj_refresh_skew_sec", "1800") or "1800"))
REFRESH_CHECK_SEC = int(float(os.getenv("qwdj_refresh_check_sec", "300") or "300"))  # 看守检查间隔

# ---------------- 随机 UA（安卓 WebView）----------------
_UA_MODELS = ["22041211AC", "2201122C", "2211133C", "23013RK75C", "M2012K11AC", "M2101K9C",
              "V2183A", "V2055A", "PDRM00", "PEEM00", "RMX3562", "RMX3121",
              "SM-G9910", "SM-A5360", "ANA-AN00", "ELS-AN00", "PGT-AN20", "2210132C"]
_UA_BUILDS = ["UP1A.231005.007", "TP1A.220624.014", "SP1A.210812.016", "TKQ1.221114.001",
              "UKQ1.230917.001", "RKQ1.211001.001", "SKQ1.220303.001"]
_UA_ANDROID = ["12", "13", "14"]
_UA_CHROME_MAJOR = [118, 120, 122, 124, 126, 128, 130]


def random_ua(seed=None) -> str:
    """seed 非空时按 seed 派生（同账号每次一样，设备持久化）；否则纯随机。"""
    rng = random.Random(seed) if seed is not None else random
    android = rng.choice(_UA_ANDROID)
    model = rng.choice(_UA_MODELS)
    build = rng.choice(_UA_BUILDS)
    chrome = f"{rng.choice(_UA_CHROME_MAJOR)}.0.{rng.randint(4000, 6999)}.{rng.randint(50, 199)}"
    return (f"Mozilla/5.0 (Linux; Android {android}; {model} Build/{build}; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
            f"Chrome/{chrome} Mobile Safari/537.36")


# ---------------- 代理池（芳华同款：提取API + 失败轮换）----------------
class ProxyPool:
    _IP_PORT = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}")

    def __init__(self, api_url: str):
        self.api_url = (api_url or "").strip()
        self.proxy = None
        self.lock = threading.Lock()

    def enabled(self) -> bool:
        return bool(self.api_url)

    def _extract(self, text: str):
        m = self._IP_PORT.search(text or "")
        return m.group(0) if m else None

    def fetch(self):
        """取一个新代理 ip:port"""
        if not self.api_url:
            return None
        try:
            r = requests.get(self.api_url, timeout=10, verify=False,
                             headers={"User-Agent": "Mozilla/5.0"})
            p = self._extract(r.text)
            with self.lock:
                self.proxy = p
            return p
        except Exception:
            return None

    def proxies(self):
        with self.lock:
            if not self.proxy:
                return None
            return {"http": f"http://{self.proxy}", "https": f"http://{self.proxy}"}

    def rotate(self):
        return self.fetch()


class ParallelBot:
    def __init__(self):
        self.proxy_api = os.getenv("qwdj_proxy", "").strip()
        self.account_list = self._get_accounts()
        self.running = False
        self.threads = []

    def _get_accounts(self):
        """读取账号（qwdj：备注#token&备注#token）；UA 每账号随机；代理每账号一个池"""
        qwdj = os.getenv("qwdj")
        if not qwdj:
            print("⚠️ 未配置qwdj环境变量")
            return []
        accounts = []
        # 账号分隔符：& 或换行（\r\n / \n / \r），两者可混用
        for idx, item in enumerate(re.split(r"[&\r\n]+", qwdj), 1):
            item = item.strip()
            if not item:
                continue
            if "#" not in item:
                print(f"❌ 账号{idx}格式错误(应为 备注#token)")
                continue
            parts = [p.strip() for p in item.split("#")]
            remark = parts[0] or f"账号{idx}"
            auth = parts[1] if len(parts) > 1 else ""       # "Bearer eyJ..." (SDK刷金币)
            app_token = parts[2] if len(parts) > 2 else ""  # app令牌(可选)，用于 Bearer 过期自动换新
            if not auth:
                print(f"❌ 账号{idx} 缺少令牌")
                continue
            dev_id = hashlib.sha256(auth.encode()).hexdigest()   # 稳定的 64hex deviceId
            accounts.append({
                "idx": idx,
                "remark": remark,
                "auth": auth,                          # 完整 "Bearer eyJ..."（会被自动刷新覆盖）
                "app_token": app_token,                # 第3段：换新Bearer用（无则不能自动刷新）
                "app_dev": hashlib.md5(app_token.encode()).hexdigest()[:16] if app_token else "",  # app接口16hex设备(服务端不校验)
                "ua": random_ua(seed=auth),            # H5 WebView UA：按账号派生，同号每次一样(设备持久化)
                "device_id": dev_id,
                "sdk_ua": f"root:false vpn:false emulator:false debug:false deviceId:{dev_id}",  # SDK签名类接口的设备风控UA
                "proxy_mgr": ProxyPool(self.proxy_api),
            })
        return accounts

    # ---------------- Bearer 自动刷新 ----------------
    def _jwt_exp(self, bearer: str) -> int:
        """解出 Bearer(JWT) 的 exp 时间戳；解析失败返回 0。"""
        try:
            tok = bearer.split(" ", 1)[1] if bearer.lower().startswith("bearer") else bearer
            p = tok.split(".")[1]
            p += "=" * (-len(p) % 4)
            return int(json.loads(base64.urlsafe_b64decode(p)).get("exp", 0))
        except Exception:
            return 0

    def _app_hdr(self, account):
        return {"token": account.get("app_token", ""), "deviceId": account.get("app_dev", ""),
                "client": "app", "deviceType": "Android", "User-Agent": "okhttp/4.12.0"}

    def _refresh_bearer(self, account) -> bool:
        """用第3段 app令牌换一个新的 24h Bearer，成功则更新 account['auth']。"""
        idx = account["remark"]
        app_token = account.get("app_token")
        if not app_token:
            return False
        try:
            # 1) userInfo 拿 uid/昵称/手机号（换新链需要）
            r = self._http(account, "get", f"{APP_API}/v1/app/user/userInfo", headers=self._app_hdr(account))
            d = (r.json().get("data") or {})
            uid, nick, phone = d.get("id"), d.get("nickName") or "", d.get("userName") or ""
            if uid is None:
                print(f"🔑 {idx} 刷新失败：app令牌可能已过期(userInfo无data)。需用登录机重登")
                return False
            # 2) PKCE
            cv = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
            cc = base64.urlsafe_b64encode(hashlib.sha256(cv.encode()).digest()).decode().rstrip("=")
            # 3) xjsdk/auth 拿 authCode
            hj = {**self._app_hdr(account), "Content-Type": "application/json;charset=UTF-8"}
            r = self._http(account, "post", f"{APP_API}/v1/app/apk/xjsdk/auth", headers=hj,
                           data=json.dumps({"appId": APP_ID, "codeChallenge": cc}).encode())
            ac = ((r.json().get("data") or {}) or {}).get("authCode")
            if not ac:
                print(f"🔑 {idx} 刷新失败(authCode空): {r.text[:120]}")
                return False
            # 4) user/sync 换新 JWT
            body = {"app_id": APP_ID, "auth_code": ac, "third_user_id": str(uid),
                    "third_username": nick, "nickname": nick, "avatar_url": "",
                    "phone": phone, "inviter_third_user_id": "", "code_verifier": cv}
            r = self._http(account, "post", SDK_SYNC_URL,
                           headers={"x-app-id": APP_ID, "User-Agent": SDK_SYNC_UA,
                                    "Content-Type": "application/json;charset=UTF-8"},
                           data=json.dumps(body).encode())
            jwt = ((r.json().get("result") or {}) or {}).get("token")
            if not jwt:
                print(f"🔑 {idx} 刷新失败(sync无token): {r.text[:120]}")
                return False
            account["auth"] = "Bearer " + jwt
            exp = self._jwt_exp(jwt)
            when = time.strftime("%m-%d %H:%M", time.localtime(exp)) if exp else "?"
            print(f"🔑 {idx} ✅ Bearer已自动刷新，新到期 {when}")
            return True
        except Exception as e:
            print(f"🔑 {idx} 刷新异常: {str(e)[:60]}")
            return False

    def _ensure_bearer(self, account):
        """如 Bearer 已过期或即将过期(<REFRESH_SKEW)，用 app令牌换新。无第3段则跳过。"""
        if not account.get("app_token"):
            return
        exp = self._jwt_exp(account.get("auth", ""))
        if exp and (exp - time.time()) > REFRESH_SKEW:
            return   # 还早，无需刷新
        self._refresh_bearer(account)

    def _refresh_watch_task(self, account):
        """看守线程：定期检查 Bearer 剩余有效期，快到期就自动换新。"""
        while self.running and not account.get("capped"):
            try:
                self._ensure_bearer(account)
            except Exception as e:
                print(f"🔑 {account['remark']} 刷新看守异常: {str(e)[:50]}")
            time.sleep(REFRESH_CHECK_SEC)


    def _gen_sign(self, content):
        """生成SHA256签名"""
        return hashlib.sha256(content.encode()).hexdigest().lower()

    def _h5_headers(self, account, extra=None):
        """H5 类接口头（my-stats/exchange/宝箱/红包雨）：WebView UA + Origin + X-Requested-With"""
        h = {"Authorization": account["auth"], "User-Agent": account["ua"],
             "Origin": H5_ORIGIN, "X-Requested-With": PKG}
        if extra:
            h.update(extra)
        return h

    def _sdk_headers(self, account, sign):
        """SDK 签名类接口头（视频上报/广告上报）：设备风控 UA + X-App-Id + X-Signature"""
        return {"Authorization": account["auth"], "X-App-Id": APP_ID, "X-Signature": sign,
                "User-Agent": account["sdk_ua"], "Content-Type": "application/json"}

    def _get_coins(self, account):
        """查今日金币 today_coins；失败返回 None"""
        headers = self._h5_headers(account)
        try:
            r = self._http(account, "get", URLS["my_stats"], headers=headers)
            j = r.json()
            if j.get("success") and isinstance(j.get("result"), dict):
                res = j["result"]
                return int(res.get("today_coins") or 0), int(res.get("total_points") or 0)
        except Exception:
            pass
        return None, None

    # ---------- 带代理+失败轮换的统一请求 ----------
    def _http(self, account, method, url, **kw):
        pm = account.get("proxy_mgr")
        kw.setdefault("timeout", 15)
        kw.setdefault("verify", False)
        last = None
        for attempt in range(2):
            proxies = pm.proxies() if (pm and pm.enabled()) else None
            try:
                return requests.request(method, url, proxies=proxies, **kw)
            except Exception as e:
                last = e
                if pm and pm.enabled() and attempt == 0:
                    pm.rotate()   # 换个代理再试一次
                    continue
                raise
        raise last

    # ========== 独立任务：红包雨（带延迟） ==========
    def _red_envelope_task(self, account):
        idx = account["remark"]
        headers = self._h5_headers(account)
        try:
            resp = self._http(account, "get", URLS["red_envelope"], headers=headers)
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()["result"]["treasure_box_data"]
                print(f"🧧 {idx} 红包雨：{data['coins_gained']}金币 | 等待{data['remaining_seconds']}秒")
                if data["remaining_seconds"] > 0:
                    time.sleep(data["remaining_seconds"])
            else:
                print(f"❌ {idx} 红包雨失败: {resp.json()}")
        except Exception as e:
            print(f"❌ {idx} 红包雨异常：{str(e)[:30]}")

    # ========== 独立任务：宝箱领取 ==========
    def _treasure_task(self, account):
        idx = account["remark"]
        headers = self._h5_headers(account)
        try:
            resp = self._http(account, "get", URLS["treasure"], headers=headers)
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()["result"]["treasure_box_data"]
                print(f"🎁 {idx} 宝箱：{data['coins_gained']}金币")
            else:
                print(f"❌ {idx} 宝箱领取失败")
        except Exception as e:
            print(f"❌ {idx} 宝箱异常：{str(e)[:30]}")

    # ========== 独立任务：视频上报（循环） ==========
    def _video_report_task(self, account):
        idx = account["remark"]
        while self.running and not account.get("capped"):
            try:
                ts = str(int(time.time() * 1000))
                json_str = f'{{"watch_type":"short_drama","action_id":"{ts}","duration":{FIXED_DURATION}}}'
                sign = self._gen_sign(f"{APP_ID}{ts}{json_str}{SIGN_KEY}")
                headers = self._sdk_headers(account, sign)
                resp = self._http(account, "post", URLS["video_report"], headers=headers, data=json_str)
                if resp.status_code == 200 and resp.json().get("success"):
                    print(f"📺 {idx} 视频上报成功")
                else:
                    print(f"❌ {idx} 视频上报失败")
            except Exception as e:
                print(f"❌ {idx} 视频上报异常：{str(e)[:30]}")
            time.sleep(60)

    # ========== 独立任务：广告上报（循环） ==========
    def _ad_report_task(self, account):
        idx = account["remark"]
        while self.running and not account.get("capped"):
            try:
                ts = str(int(time.time() * 1000))
                ad_points = random.randint(*AD_POINTS_RANGE)
                bid = str(uuid.uuid4())   # 广告实例ID(客户端随机UUID)，服务器只当去重键，缺了会被判"无效/验证失败"
                json_str = (f'{{"ad_points":{ad_points},"ad_type":"incentive","remark":"激励广告",'
                            f'"b_id":"{bid}","action_id":"{ts}"}}')
                sign = self._gen_sign(f"{APP_ID}{ts}{json_str}{SIGN_KEY}")
                headers = self._sdk_headers(account, sign)
                resp = self._http(account, "post", URLS["ad_report"], headers=headers, data=json_str)
                if resp.status_code == 200 and resp.json().get("success"):
                    print(f"📊 {idx} 广告上报：{ad_points}积分")
                else:
                    print(f"❌ {idx} 广告上报失败")
            except Exception as e:
                print(f"❌ {idx} 广告上报异常：{str(e)[:30]}")
            time.sleep(random.randint(60, 120))

    # ========== 独立任务：积分兑换（循环） ==========
    def _exchange_task(self, account):
        idx = account["remark"]
        headers = self._h5_headers(account, {"Content-Type": "application/json"})
        loop_count = 1
        while self.running and not account.get("capped") and loop_count <= MAX_LOOP:
            # 先查金币，够 200W 就停掉整个账号
            coins, points = self._get_coins(account)
            if coins is not None:
                if coins >= COIN_CAP:
                    account["capped"] = True
                    print(f"🏁 {idx} 今日金币 {coins:,} ≥ {COIN_CAP:,}，停止该账号所有任务")
                    break
                print(f"💰 {idx} 当前金币 {coins:,} / 目标 {COIN_CAP:,} | 剩余积分 {points:,}")
            try:
                resp = self._http(account, "post", URLS["exchange"], headers=headers,
                                  json={"source_type": "points", "watch_type": ""})
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()["result"]
                    print(f"🎉 {idx} 兑换{loop_count}：{data['coins_gained']}金币 | 剩余{data['current_points']}积分")
                else:
                    error_data = resp.json()
                    print(f"❌ {idx} 兑换{loop_count}失败: {error_data}")
                    if error_data.get("code") == 50101:
                        print(f"⚠️ {idx} 积分不足，停止兑换")
                        break
                    if error_data.get("code") == 50450 and error_data.get("message") == '操作过于频繁，请稍后再试':
                        time.sleep(5)
            except Exception as e:
                print(f"❌ {idx} 兑换{loop_count}异常：{str(e)[:30]}")
            time.sleep(EXCHANGE_INTERVAL)
            loop_count += 1
        print(f"🔚 {idx} 兑换任务结束")

    # ========== 启动单个账号的所有并行任务 ==========
    def _start_account_tasks(self, account):
        idx = account["remark"]
        print(f"\n========== {idx} 启动所有任务 ==========")
        pm = account.get("proxy_mgr")
        if pm and pm.enabled():
            p = pm.fetch()   # 预取一个代理
            print(f"🌐 {idx} 代理: {p or '获取失败(将直连/重试)'}")
        else:
            print(f"🌐 {idx} 代理: 未配置(直连)")

        # 启动即确保 Bearer 有效（过期/将过期则先用 app令牌换新），随后起刷新看守线程
        if account.get("app_token"):
            self._ensure_bearer(account)
            wt = threading.Thread(target=self._refresh_watch_task, args=(account,), daemon=True)
            wt.start()
            self.threads.append(wt)
        else:
            print(f"🔑 {idx} 未提供 app令牌(2段格式)，Bearer 过期后需用登录机重登")

        targets = [self._red_envelope_task, self._treasure_task,
                   self._video_report_task, self._exchange_task]
        if AD_REPORT_ENABLED:
            targets.insert(3, self._ad_report_task)   # 默认不启用（会 50701 疑似刷量）
        else:
            print(f"⏭️ {idx} 已跳过广告上报(穿山甲S2S校验,防风控)")
        for target in targets:
            t = threading.Thread(target=target, args=(account,), daemon=True)
            t.start()
            self.threads.append(t)

    # ========== 主启动函数 ==========
    def run(self):
        if not self.account_list:
            print("❌ 无有效账号，退出")
            return
        self.running = True
        print(f"📌 检测到{len(self.account_list)}个账号 | 代理: {'开启' if self.proxy_api else '关闭'} | 所有任务并行启动")
        for account in self.account_list:
            self._start_account_tasks(account)
            time.sleep(2)
        print("\n✅ 所有任务已并行启动 | 按Ctrl+C停止")
        try:
            while self.running:
                if self.account_list and all(a.get("capped") for a in self.account_list):
                    print("🏁 所有账号均已达金币上限，任务结束")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\n🛑 脚本停止，所有线程将退出")
            for t in self.threads:
                t.join(timeout=2)


if __name__ == "__main__":
    bot = ParallelBot()
    bot.run()
