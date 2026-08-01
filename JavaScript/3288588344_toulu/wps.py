"""
WPS · 每日签到 + 福利中心(打卡/抽奖/会员试用申请/限量爆款领取)+ 小程序每日打卡,送积分与会员时长

抓取: 打开「WPS」 → 进任意活动页(任务中心/福利中心/天天领福利)→ 抓包https://personal-act.wps.cn/activity-rubik/activity/page_info或者www.kdocs.cn域名下
获取 wps_sid

多账号支持: wps_sid 使用 & 或换行分割

`wps_sid`    `V02StZ...&V02xxx...`    ✅  (必填，多账号用 & 或换行分割)
`wps_task_hot`    `false`    ❌（不写默认开）
`wps_task_signin`    `false`    ❌（不写默认开）
`wps_task_trial`    `false`    ❌（不写默认开）
`wps_task_fragment`    `false`    ❌（不写默认开）
`wps_task_lottery`    `false`    ❌（不写默认开）
`wps_task_clockin`    `false`    ❌（不写默认开）
`wps_debug`    `true`    ❌（不写默认关）

依赖: pip install requests cryptography
"""

import os
import sys
import json
import time
import random
import re
import base64
import urllib.parse
from datetime import datetime, timezone, timedelta
import hashlib
import hmac

# 设置标准输出为 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.backends import default_backend
except ImportError as e:
    print("[ERROR] 缺少 cryptography, 请先执行: pip install cryptography")
    sys.exit(1)

try:
    import requests
except ImportError as e:
    print("[ERROR] 缺少 requests, 请先执行: pip install requests")
    sys.exit(1)

# ==================== 配置与常量 ====================
SCRIPT_VERSION = "1.0.0"
CK_KEY = "wps_sid"
ANNOUNCEMENT_URL = "https://github.com/3288588344/toulu/raw/refs/heads/main/tl.json"

# 福利中心活动「WPS618 天天领福利」的组件标识(活动换期需更新)
FLZX = {"activity_number": "HD2025031721339450", "page_number": "YM2025060910400185"}
FLZX_POSITION = "ios_flzx_grzxsdjg3001"

COMPONENTS = {
    "fragment": {"component_number": "ZJ2025061815352884", "component_node_id": "FN1769668388sb3w", "type": 42},
    "lottery": {"component_number": "ZJ2025092916519174", "component_node_id": "FN1779447163CApn", "type": 45, "session_id": 3002},
    "trial": {"component_number": "ZJ2025041115207603", "component_node_id": "FN1744359116PWbV", "type": 32},
    "hot": {"component_number": "ZJ2025041115200788", "component_node_id": "FN1744358694RbIn", "type": 31},
}

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 WpsiOS/26.6.1"
MINI_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN miniProgram"

ACTION_GAP = [5, 10]
ACCOUNT_GAP = [10, 20]  # 账号之间间隔

# 接口
ISLOGIN = "https://account.wps.cn/api/v3/islogin"
ENC_KEY = "https://personal-bus.wps.cn/sign_in/v1/encrypt/key"
DAY_INFO = "https://personal-bus.wps.cn/sign_in/v1/day_info"
SIGN_IN = "https://personal-bus.wps.cn/sign_in/v1/sign_in"
COMPONENT = "https://personal-act.wps.cn/activity-rubik/activity/component_action"
PAGE_INFO = "https://personal-act.wps.cn/activity-rubik/activity/page_info"

CLOCK_INFO = "https://personal-bus.wps.cn/activity/clock_in/v1/info"
CLOCK_IN = "https://personal-bus.wps.cn/activity/clock_in/v1/clock_in"
CLOCK_REWARD = "https://personal-bus.wps.cn/activity/clock_in/v1/reward"
CLOCK_CONF = "https://personal-act.wpscdn.cn/srcapi/act/rubik-service/honeycomb-adapter/client/module-info?pid=113&mg_id=47736&id=48312"

# ==================== 通知 ====================
def safe_print(text):
    """安全打印，处理编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        clean = text.encode("utf-8", errors="replace").decode("utf-8")
        print(clean)


try:
    from notify import send as _notify_send

    def notify(title, subtitle="", body=""):
        safe_print(f"\n====[Notice] {title}====\n{subtitle}\n{body}\n")
        txt = f"{subtitle}\n{body}" if subtitle else body
        _notify_send(title, txt)
except ImportError:
    def notify(title, subtitle="", body=""):
        safe_print(f"\n====[Notice] {title}====\n{subtitle}\n{body}\n")


# ==================== 公告 ====================
def fetch_announcement():
    """从远程URL获取公告内容"""
    try:
        resp = requests.get(ANNOUNCEMENT_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, str):
                return data.strip()
            elif isinstance(data, dict):
                announcement = data.get("author_note", "")
                if announcement:
                    resources = data.get("resources", {})
                    community = data.get("community", {})
                    contact = data.get("contact", {})
                    services = data.get("services", {})

                    lines = [announcement, ""]
                    if resources:
                        lines.append("=" * 40)
                        lines.append("[资源]")
                        if resources.get("github"):
                            lines.append(f"GitHub: {resources['github']}")
                        if resources.get("homepage"):
                            lines.append(f"主页: {resources['homepage']}")
                    if community:
                        lines.append("=" * 40)
                        lines.append("[社区]")
                        if community.get("qq_channel"):
                            qq = community["qq_channel"]
                            lines.append(f"QQ频道: {qq.get('url', '')} ({qq.get('description', '')})")
                        if community.get("telegram_channel"):
                            lines.append(f"Telegram: {community['telegram_channel']}")
                    if contact:
                        lines.append("=" * 40)
                        lines.append("[联系方式]")
                        if contact.get("wechat_official_account"):
                            lines.append(f"微信公众号: {contact['wechat_official_account']}")
                        if contact.get("personal_wechat"):
                            lines.append(f"个人微信: {contact['personal_wechat']}")
                        if contact.get("email"):
                            lines.append(f"邮箱: {contact['email']}")
                        if contact.get("wechat_miniprogram"):
                            lines.append(f"小程序: {contact['wechat_miniprogram']}")
                    if services:
                        lines.append("=" * 40)
                        lines.append("[服务]")
                        if services.get("submission"):
                            lines.append(f"投稿: {services['submission']}")
                        if services.get("paid_service"):
                            lines.append(f"付费服务: {services['paid_service']}")
                    return "\n".join(lines)
                return data.get("content", data.get("announcement", ""))
            elif isinstance(data, list) and len(data) > 0:
                return data[0].get("content", str(data[0]))
        return None
    except Exception as e:
        debug(f"获取公告失败: {e}")
        return None


def show_announcement():
    """获取并显示公告"""
    announcement = fetch_announcement()
    if announcement:
        print("\n" + "=" * 50)
        print("[Announcement]")
        print("=" * 50)
        print(announcement)
        print("=" * 50 + "\n")
    return announcement


# ==================== 工具函数 ====================
results = []
all_results = []  # 所有账号的结果汇总


def log(*args):
    print("\n".join(str(a) for a in args))


def debug(content):
    if os.environ.get("wps_debug", "false").lower() != "true":
        return
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    log(f"[DEBUG] {text}")


def task_off(k):
    """任务开关: 环境变量设为 false/0/FALSE 才关闭, 未设置默认开启"""
    v = os.environ.get(k)
    return v in ("false", "0", "FALSE", "False")


def http_date():
    return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def beijing_date():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def sleep(ms):
    time.sleep(ms / 1000)


def jitter(min_max):
    min_s, max_s = min_max
    return int((min_s + random.random() * (max_s - min_s)) * 1000)


def safe_json(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def classify(msg, done_label=None):
    m = str(msg or "")
    if not m:
        return {"e": "⚠️", "t": "未成功"}
    if re.search(r"已签|has sign", m, re.I):
        return {"e": "✅", "t": "已签到"}
    if re.search(r"Duplicate entry|已领取|已申领|已参与|已参加|已报名|已完成|重复|repeat|already", m, re.I):
        return {"e": "✅", "t": done_label or "已完成"}
    if re.search(r"无.*次数|没有.*次数|次数.*(用完|不足|为0)|达到?.*上限|已达.*上限|超(出|过).*次数|reach limit|out of limit|上限", m, re.I):
        return {"e": "✅", "t": "已达上限"}
    if re.search(r"售罄|领完|抢完|发完|抢光|领光|out of stock|库存(不足)?|no stock|sold out|stock", m, re.I):
        return {"e": "⚠️", "t": "已领完"}
    if re.search(r"资格|不满足|未满足|不符合|无权限|没有权限|没有资格|not (match|qualified)|不在.*(范围|名单)|未达条件", m, re.I):
        return {"e": "⚠️", "t": "没资格"}
    return {"e": "⚠️", "t": (m[:30] + "…") if len(m) > 30 else m}


# ==================== 多账号解析 ====================
def parse_accounts():
    """解析环境变量中的多账号，支持 & 和换行分割"""
    sid_raw = os.environ.get(CK_KEY, "")
    if not sid_raw:
        return []
    # 支持 & 或换行分割
    sids = re.split(r'[&\n]+', sid_raw)
    # 过滤空值并去重
    accounts = []
    seen = set()
    for sid in sids:
        sid = sid.strip()
        if sid and sid not in seen:
            seen.add(sid)
            accounts.append(sid)
    return accounts


# ==================== 加密工具 ====================
def gen_aes_key():
    cs = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = "".join(random.choice(cs) for _ in range(22))
    return s + str(int(time.time()))


def aes_encrypt(plain, key_str, iv_str):
    key = key_str.encode("utf-8")
    iv = iv_str.encode("utf-8")
    plain_bytes = plain.encode("utf-8")
    pad_len = 16 - (len(plain_bytes) % 16)
    padded = plain_bytes + bytes([pad_len] * pad_len)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ct).decode("utf-8")


def rsa_encrypt_b64(msg, pem_b64):
    pem_bytes = base64.b64decode(pem_b64)
    public_key = serialization.load_pem_public_key(pem_bytes, backend=default_backend())
    encrypted = public_key.encrypt(msg.encode("utf-8"), asym_padding.PKCS1v15())
    return base64.b64encode(encrypted).decode("utf-8")


def md5_hex(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def hmac_sha256_hex(msg_str, key_str):
    return hmac.new(key_str.encode("utf-8"), msg_str.encode("utf-8"), hashlib.sha256).hexdigest()


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


# ==================== HTTP 封装 (支持多账号上下文) ====================
class WPSContext:
    """WPS 账号上下文，每个账号独立"""
    def __init__(self, sid):
        self.sid = sid
        self.uid = None
        self.results = []
        self.masked_sid = sid[:6] + "***" if len(sid) > 6 else sid

    def http_req(self, method, url, body=None, token=None):
        headers = {
            "User-Agent": UA,
            "Cookie": f"wps_sid={self.sid}; wps_sids={self.sid}",
            "Origin": "https://personal-act.wps.cn",
            "Referer": "https://personal-act.wps.cn/",
        }
        if body:
            headers["Content-Type"] = "application/json"
        if token:
            headers["token"] = token
        data = body.encode("utf-8") if isinstance(body, str) else body
        resp = requests.request(method, url, headers=headers, data=data, timeout=30)
        return {"status": resp.status_code, "body": resp.text}

    def raw_req(self, method, url, body=None, date=None, signature=None):
        headers = {"User-Agent": MINI_UA, "Accept": "*/*", "X-CSRFToken": "1234567890"}
        headers["Cookie"] = f"wps_sid={self.sid};csrf=1234567890"
        if body:
            headers["Content-Type"] = "application/json"
        if signature:
            headers["Signature"] = signature
        if date:
            headers["Date"] = date
        data = body.encode("utf-8") if isinstance(body, str) else body
        resp = requests.request(method, url, headers=headers, data=data, timeout=30)
        return {"status": resp.status_code, "body": resp.text}

    def log_result(self, text):
        self.results.append(text)

    def get_results(self):
        return self.results


# ==================== 福利中心 page_info 复用 ====================
def fetch_page_info(ctx):
    filter_params = json.dumps({"cs_from": "", "mk_key": "", "position": FLZX_POSITION}, separators=(",", ":"))
    url = f"{PAGE_INFO}?activity_number={FLZX['activity_number']}&page_number={FLZX['page_number']}&filter_params={urllib.parse.quote(filter_params)}"
    try:
        r = ctx.http_req("GET", url)
        j = safe_json(r["body"])
        if not j or j.get("result") != "ok" or not isinstance(j.get("data"), list):
            debug(f"page_info 异常: {r['body'][:300]}")
            return None
        return j["data"]
    except Exception as e:
        debug(f"page_info 异常: {e}")
        return None


def find_comp(lst, number, node=None):
    if not lst:
        return None
    for c in lst:
        if c and c.get("number") == number and (not node or c.get("component_node_id") == node):
            return c
    return None


# ==================== 任务:每日签到 ====================
def task_sign_in(ctx):
    tag = "每日签到"
    try:
        di = ctx.http_req("GET", DAY_INFO)
        info = (safe_json(di["body"]) or {}).get("data", {}).get("info", {})
        if info.get("has_sign"):
            ctx.log_result(f"✅ {tag}:已签到")
            return

        ek = ctx.http_req("GET", ENC_KEY)
        pub_key_b64 = (safe_json(ek["body"]) or {}).get("data")
        if not pub_key_b64:
            raise Exception(f"公钥获取失败: {ek['body'][:120]}")

        aes_key = gen_aes_key()
        plain = json.dumps({"user_id": ctx.uid, "platform": 32}, separators=(",", ":"))
        extra = aes_encrypt(plain, aes_key, aes_key[:16])
        token = rsa_encrypt_b64(aes_key, pub_key_b64)

        body = json.dumps({"encrypt": True, "extra": extra, "pay_origin": "ios_ucs_rwzx sign", "channel": ""}, separators=(",", ":"))
        r = ctx.http_req("POST", SIGN_IN, body=body, token=token)
        j = safe_json(r["body"])
        if j and j.get("result") == "ok":
            names = [x.get("reward_name") for x in (j.get("data") or {}).get("rewards", []) if x.get("reward_name")]
            ctx.log_result(f"✅ {tag}:成功{' ' + '/'.join(names) if names else ''}")
        else:
            st = classify(j.get("ext_msg") or j.get("msg"), "已签到")
            ctx.log_result(f"{st['e']} {tag}:{st['t']}")
            if st["e"] != "✅":
                debug(f"{tag} 响应: {r['body'][:300]}")
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 任务:限量爆款 ====================
def task_hot(ctx):
    tag = "限量爆款"
    comp = COMPONENTS["hot"]
    try:
        lst = fetch_page_info(ctx)
        if not lst:
            ctx.log_result(f"❌ {tag}:page_info 无响应")
            return
        node = find_comp(lst, comp["component_number"], comp["component_node_id"])
        ps = (node.get("privilege_select") or {}) if node else {}
        details = ps.get("privilege_select_details") or []
        if not details:
            ctx.log_result(f"⚠️ {tag}:未找到爆款组件(可能已换期,需重抓)")
            return

        if ps.get("select_reach_limit"):
            ctx.log_result(f"✅ {tag}:已领取(今日已选)")
            return

        def score(d):
            return (10000 if d.get("privilege_type") == "privilege" else 0) + (d.get("hours") or 0) * 100 + (d.get("nums") or 0)

        ranked = sorted(details, key=score, reverse=True)

        done = False
        for d in ranked:
            req_obj = {
                "component_uniq_number": {
                    "activity_number": FLZX["activity_number"],
                    "page_number": FLZX["page_number"],
                    "component_number": comp["component_number"],
                    "component_node_id": comp["component_node_id"],
                },
                "component_type": comp["type"],
                "component_action": "privilege_select.exec",
                "privilege_select": {"group_id": d["group_id"], "privilege_id": d["privilege_id"]},
            }
            r = ctx.http_req("POST", COMPONENT, body=json.dumps(req_obj, separators=(",", ":")))
            j = safe_json(r["body"])
            inner = (j.get("data") or {}).get("privilege_select") or {}
            if j and j.get("result") == "ok" and inner.get("success") is True:
                ctx.log_result(f"✅ {tag}:成功 {d.get('title') or 'pid ' + str(d.get('privilege_id'))}")
                done = True
                break
            debug(f"{tag} {d.get('title')}(pid {d.get('privilege_id')})未中: {r['body'][:200]}")
        if not done:
            ctx.log_result(f"⚠️ {tag}:未领到(超级会员已秒光、其余也没抢到)")
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 任务:福利中心打卡免费领会员 ====================
def task_fragment(ctx):
    tag = "打卡领会员"
    comp = COMPONENTS["fragment"]
    try:
        today = beijing_date()

        lst = fetch_page_info(ctx)
        node = find_comp(lst, comp["component_number"])
        if not node:
            ctx.log_result(f"⚠️ {tag}:未取到序列状态,跳过(避免误清零连续天数)")
            debug(f"{tag} page_info 未含 fragment 组件 {comp['component_number']}")
            return
        fc = node.get("fragment_collect") or {}
        series_id = fc.get("sign_series_id") or ""
        records = fc.get("sign_records") or []

        records_info = ",".join(f"{r.get('sign_date')}:{r.get('sign_status')}" for r in records)
        debug(f'{tag} 读到 series_id={series_id or "(空)"} records={records_info}')

        today_rec = next((r for r in records if r and r.get("sign_date") == today), None)
        if today_rec and today_rec.get("sign_status") == "signed":
            ctx.log_result(f"✅ {tag}:已打卡")
            return

        is_new = not series_id
        req_obj = {
            "component_uniq_number": {
                "activity_number": FLZX["activity_number"],
                "page_number": FLZX["page_number"],
                "component_number": comp["component_number"],
                "component_node_id": comp["component_node_id"],
            },
            "component_type": comp["type"],
            "component_action": "fragment_collect.sign_in",
            "fragment_collect": {"sign_date": today, "series_id": series_id, "is_new_sign_series": is_new},
        }
        r = ctx.http_req("POST", COMPONENT, body=json.dumps(req_obj, separators=(",", ":")))
        j = safe_json(r["body"])
        if not j:
            ctx.log_result(f"❌ {tag}:无响应")
            debug(f"{tag} 响应: {r['body'][:300]}")
            return
        if j.get("result") != "ok":
            st = classify(j.get("msg") or j.get("ext_msg"), "已打卡")
            ctx.log_result(f"{st['e']} {tag}:{st['t']}")
            if st["e"] != "✅":
                debug(f"{tag} 响应: {r['body'][:300]}")
            return
        inner = (j.get("data") or {}).get("fragment_collect") or {}
        if inner.get("success") is True:
            ctx.log_result(f"✅ {tag}:成功{'(新序列)' if is_new else ''}")
        else:
            st = classify(inner.get("reason") or j.get("msg"), "已打卡")
            ctx.log_result(f"{st['e']} {tag}:{st['t']}")
            if st["e"] != "✅":
                debug(f"{tag} 响应: {r['body'][:300]}")
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 任务:天天抽奖 ====================
def task_lottery(ctx):
    tag = "天天抽奖"
    comp = COMPONENTS["lottery"]
    try:
        lst = fetch_page_info(ctx)
        node = find_comp(lst, comp["component_number"], comp["component_node_id"])
        lv = (node.get("lottery_v2") or {}) if node else {}
        sessions = lv.get("lottery_list") or []
        sess = next((s for s in sessions if s and s.get("session_status") == "IN_PROGRESS"), None)
        if not sess and sessions:
            sess = sessions[0]
        session_id = (sess.get("session_id") if sess else None) or comp.get("session_id")
        times = (sess.get("times") if sess else 0) or 0

        if times < 1:
            ctx.log_result(f"✅ {tag}:今日暂无免费次数")
            return

        req_obj = {
            "component_uniq_number": {
                "activity_number": FLZX["activity_number"],
                "page_number": FLZX["page_number"],
                "component_number": comp["component_number"],
                "component_node_id": comp["component_node_id"],
            },
            "component_type": comp["type"],
            "component_action": "lottery_v2.exec",
            "lottery_v2": {"session_id": session_id},
        }
        r = ctx.http_req("POST", COMPONENT, body=json.dumps(req_obj, separators=(",", ":")))
        j = safe_json(r["body"])
        inner = (j.get("data") or {}).get("lottery_v2") or {}
        if j and j.get("result") == "ok" and inner.get("success") is True:
            ctx.log_result(f"✅ {tag}:成功{inner.get('reward_name', '')}")
        else:
            reason = inner.get("send_msg") or ""
            if not reason and inner.get("error_code") == 10005:
                reason = "次数用完"
            st = classify(reason or (j.get("msg") if j else None), "已完成")
            ctx.log_result(f"{st['e']} {tag}:{st['t']}")
            if st["e"] != "✅":
                debug(f"{tag} 响应: {r['body'][:300]}")
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 任务:会员免费试用 ====================
def task_trial(ctx):
    tag = "会员试用"
    try:
        base = {
            "activity_number": FLZX["activity_number"],
            "page_number": FLZX["page_number"],
            "component_number": COMPONENTS["trial"]["component_number"],
            "component_node_id": COMPONENTS["trial"]["component_node_id"],
        }

        def call_trial(action, extra):
            req_obj = {
                "component_uniq_number": base,
                "component_type": COMPONENTS["trial"]["type"],
                "component_action": action,
            }
            for k, v in extra.items():
                req_obj[k] = v
            r = ctx.http_req("POST", COMPONENT, body=json.dumps(req_obj, separators=(",", ":")))
            return safe_json(r["body"])

        def short(t):
            return re.sub(r"超级会员", "", str(t or "奖品"))

        pv = call_trial("divide_prize.preview", {})
        details = (((pv or {}).get("data") or {}).get("divide_prize") or {}).get("divide_prize_details") or []
        if not details or all(d.get("has_join") for d in details):
            ctx.log_result(f"✅ {tag}:全部已申请")
            return

        parts = []
        all_good = True
        acted = 0
        for d in details:
            name = short(d.get("title"))
            if d.get("has_join"):
                parts.append(f"{name}已申请")
                continue
            if d.get("stock") is not None and d.get("stock") <= 0:
                parts.append(f"{name}已领完")
                all_good = False
                continue
            if acted > 0:
                sleep(jitter(ACTION_GAP))
            acted += 1
            su = call_trial("divide_prize.sign_up", {
                "divide_prize": {"cycle_id": d["cycle_id"], "session_id": f"{d['session_id']}_{beijing_date()}"},
            })
            inner = ((su or {}).get("data") or {}).get("divide_prize") or {}
            if su and su.get("result") == "ok" and inner.get("success") is True:
                parts.append(f"{name}✓")
            else:
                st = classify(inner.get("reason") or (su.get("msg") if su else None), "已申请")
                parts.append(f"{name}{st['t']}")
                if st["e"] != "✅":
                    all_good = False
                    debug(f"{tag} {d.get('title')}: {json.dumps(su)[:200]}")
        ctx.log_result(f"✅ {tag}:全部已申请" if all_good else f"⚠️ {tag}:{' '.join(parts)}")
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 任务:小程序每日打卡 ====================
def claim_clock_in_rewards(ctx, inf_body, s_key, ss):
    try:
        lst = (((safe_json(inf_body) or {}).get("data") or {}).get("reward_list") or {}).get("list") or []
        pend = [rw for rw in lst if rw and rw.get("reward_status") == 1]
        reward_info = " ".join(f"{rw.get('reward_id')}={rw.get('reward_status')}" for rw in lst)
        debug(f'奖励表({len(lst)}): {reward_info or "空"}')
        if not pend:
            ctx.log_result("ℹ️ 昨日奖励:暂无可领(未到开放时间)" if lst else "⚠️ 领奖:未取到奖励列表")
            return

        got, fail = [], []
        for rw in pend:
            body = canonical_json({"client_type": 1, "reward_id": rw["reward_id"], "clock_in_time": rw["clock_in_time"]})
            date = http_date()
            signature = hmac_sha256_hex(s_key + md5_hex(body) + date, ss)
            r = ctx.raw_req("POST", CLOCK_REWARD, body=body, date=date, signature=signature)
            j = safe_json(r["body"])
            name = rw.get("sku_name") or rw.get("mb_name") or "奖励"
            if j and j.get("result") == "ok" and (j.get("data") or {}).get("reward_status") is True:
                got.append(name)
            else:
                fail.append(name)
                debug(f"领奖 {name}({rw.get('reward_id')}) 失败: {r['body'][:200]}")
            sleep(jitter(ACTION_GAP))
        if got:
            ctx.log_result(f"✅ 领昨日奖励:{'、'.join(got)}")
        if fail:
            ctx.log_result(f"⚠️ 待领奖励未领成功(可去小程序手动领):{'、'.join(fail)}")
    except Exception as e:
        log(f"[ERROR] 领昨日奖励: {e}")


def task_clock_in(ctx):
    tag = "小程序打卡"
    try:
        sleep(jitter([3, 10]))

        ss = ""
        cf_body = ""
        for i in range(2):
            if i > 0:
                sleep(2000)
            try:
                cf = ctx.raw_req("GET", CLOCK_CONF)
                cf_body = cf["body"]
                ss = (((safe_json(cf_body) or {}).get("data") or {}).get("value") or {}).get("ss")
                if ss:
                    break
            except Exception as e:
                log(f"[WARN] CLOCK_CONF 重试 {i+1}/2: {e}")

        s_key = ""
        inf_body = ""
        backoff = [0, 3000, 6000, 9000]
        for i, delay in enumerate(backoff):
            if delay:
                sleep(delay)
            try:
                inf = ctx.raw_req("GET", f"{CLOCK_INFO}?client_type=1&page_index=0&page_size=10")
                inf_body = inf["body"]
                s_key = ((safe_json(inf_body) or {}).get("data") or {}).get("s_key")
                if s_key:
                    break
                debug(f"{tag} info 重试 {i+1}/{len(backoff)}: {inf_body[:120]}")
            except Exception as e:
                debug(f"{tag} info 重试 {i+1}/{len(backoff)} 异常: {e}")

        if not ss or not s_key:
            which = "ss" if not ss else "s_key"
            src = cf_body if not ss else inf_body
            m = ((safe_json(src) or {}).get("msg")) or src[:60] or f"缺 {which}"
            ctx.log_result(f"⚠️ {tag}:接口异常(取 {which} 失败:{m})")
            debug(f"{tag} info: ss={bool(ss)} s_key={bool(s_key)} cf={cf_body[:120]} inf={inf_body[:120]}")
            return

        body_str = canonical_json({"client_type": 1})
        date = http_date()
        signature = hmac_sha256_hex(s_key + md5_hex(body_str) + date, ss)

        r = ctx.raw_req("POST", CLOCK_IN, body=body_str, date=date, signature=signature)
        j = safe_json(r["body"])
        if j and j.get("result") == "ok":
            d = j.get("data") or {}
            rw = d.get("reward_name") or (d.get("prize") or {}).get("name") or (d.get("reward") or {}).get("name") or ""
            ctx.log_result(f"✅ {tag}:成功{rw}")
        else:
            st = classify(j.get("msg") if j else None, "已打卡")
            ctx.log_result(f"{st['e']} {tag}:{st['t']}")
            if st["e"] != "✅":
                debug(f"{tag} 响应: {r['body'][:300]}")

        claim_clock_in_rewards(ctx, inf_body, s_key, ss)
    except Exception as e:
        ctx.log_result(f"❌ {tag}:异常")
        log(f"[ERROR] {tag}: {e}")


# ==================== 单个账号执行 ====================
def run_account(sid, account_index, total_accounts):
    """执行单个账号的所有任务"""
    ctx = WPSContext(sid)

    log(f"\n{'='*50}")
    log(f"[账号 {account_index}/{total_accounts}] {ctx.masked_sid}")
    log(f"{'='*50}")

    # 登录验证
    uid = None
    last_err = None
    for attempt in range(2):
        if attempt > 0:
            sleep(3000)
        try:
            r = ctx.http_req("GET", ISLOGIN)
            j = safe_json(r["body"])
            if j.get("result") != "ok" or not j.get("userid"):
                ctx.log_result(f"🚫 登录态失效: wps_sid 已过期,请重新抓取")
                log(f"[ERROR] islogin 非 ok: {r['body'][:200]}")
                return ctx
            uid = j["userid"]
            ctx.uid = uid
            log(f"[INFO] user_id 已获取({str(uid)[:3]}***)")
            break
        except Exception as e:
            last_err = e
            log(f"[WARN] islogin 网络错误({attempt+1}/2): {e}")

    if not uid:
        ctx.log_result(f"⚠️ 网络异常: islogin 请求超时")
        log(f"[ERROR] islogin 重试后仍失败: {last_err}")
        return ctx

    # 执行任务
    tasks = [
        ("wps_task_hot", lambda: task_hot(ctx)),
        ("wps_task_trial", lambda: task_trial(ctx)),
        ("wps_task_signin", lambda: task_sign_in(ctx)),
        ("wps_task_fragment", lambda: task_fragment(ctx)),
        ("wps_task_lottery", lambda: task_lottery(ctx)),
        ("wps_task_clockin", lambda: task_clock_in(ctx)),
    ]

    ran = 0
    for key, run in tasks:
        if task_off(key):
            log(f"[SKIP] {key} 已关闭")
            continue
        if ran > 0:
            sleep(jitter(ACTION_GAP))
        ran += 1
        run()

    if not ran:
        ctx.log_result("ℹ️ 所有任务均已关闭")

    return ctx


# ==================== 主流程 ====================
def main():
    global results, all_results
    results = []
    all_results = []

    accounts = parse_accounts()
    if not accounts:
        notify("WPS", "🚫 缺少 Cookie", "请先抓取 wps_sid 并设置到青龙环境变量，多账号用 & 或换行分割")
        return

    log(f"[INFO] 共检测到 {len(accounts)} 个账号")

    # 显示公告（只显示一次）
    show_announcement()

    # 逐个执行账号
    for i, sid in enumerate(accounts, 1):
        ctx = run_account(sid, i, len(accounts))
        all_results.append({
            "index": i,
            "masked_sid": ctx.masked_sid,
            "results": ctx.get_results(),
            "uid": ctx.uid
        })

        # 账号之间添加间隔（最后一个账号不需要）
        if i < len(accounts):
            gap = jitter(ACCOUNT_GAP)
            log(f"\n[INFO] 账号间隔 {gap/1000:.1f}s...")
            sleep(gap)

    # 汇总通知
    summary_lines = []
    for ar in all_results:
        status = "✅" if ar["uid"] else "❌"
        summary_lines.append(f"\n{'─'*40}")
        summary_lines.append(f"{status} [账号 {ar['index']}] {ar['masked_sid']}")
        if not ar["results"]:
            summary_lines.append("  无执行结果")
        for res in ar["results"]:
            summary_lines.append(f"  {res}")
    summary_lines.append(f"\n{'─'*40}")
    summary_lines.append(f"\n📊 总计: {len(accounts)} 个账号，成功登录 {sum(1 for a in all_results if a['uid'])} 个")

    notify_body = "\n".join(summary_lines)
    notify("WPS 任务汇总", f"共 {len(accounts)} 个账号", notify_body)

    # 控制台也输出汇总
    log("\n" + "="*50)
    log("[汇总结果]")
    log("="*50)
    log(notify_body)


if __name__ == "__main__":
    log(f"[INFO] 脚本版本 {SCRIPT_VERSION}")
    if os.environ.get("wps_clear", "").lower() in ("true", "1"):
        os.environ.pop(CK_KEY, None)
        os.environ["wps_clear"] = "false"
        notify("WPS", "", "✅ wps_sid 已清除，请重新抓取")
        sys.exit(0)
    try:
        main()
    except Exception as e:
        log(f"[ERROR] 主流程异常: {e}")
        notify("WPS", "❌ 运行异常", str(e))
