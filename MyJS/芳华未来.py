#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
芳华未来 全任务自动化脚本 v1.0
适用于青龙面板运行

环境变量: FHWL='手机号1#密码1@手机号2#密码2'
多账号用@分隔，每个账号手机号和密码用#分隔

功能清单:
1. 账密登录 + Token缓存
2. 每日签到
3. 看视频赚币（循环观看+addIntegral）
4. 视频点赞/收藏/关注达人
5. 课程学习（课程视频观看）
6. 邀请奖励领取
7. 心跳保活
8. 积分查询汇总

加密体系（逆向自apisecurity插件）:
- 请求体: AES/CBC/PKCS5Padding加密，IV=Key
- 密钥传输: RSA/ECB/PKCS1Padding加密 timestamp&aesKey
- 响应解密: RSA解密encryptedKey得AES密钥，再AES解密encryptedData
"""

import requests
import time
import random
import json
import os
import sys
import string
import base64
import threading
import hashlib
from datetime import datetime

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5, AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("⚠️ 未安装pycryptodome，将使用明文模式（建议: pip install pycryptodome）")

# ====================================== 【配置区】 ======================================
BASE_URL = "https://api.cdwjyyh.com"
TOKEN_CACHE_FILE = "fhwl_tokens.json"
ENV_VAR_NAME = "FHWL"

# 加密相关（逆向自 com.plugin.apisecurity）
RSA_PUBLIC_KEY_B64 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwVjN8e7S9Ygg2jzc+laQ"
    "EYD1YxSRppwUl1fEjfpV8CF/KvQ5IgTcyUYDe3O7/41+i7HjX2ZuwDXPOhhoVy6oD"
    "2e/NS/+XmUYLt9aEzo+erbq2+uxjwK93t0akM5C9xZDa4Ji0M5ICfZMx8pt56fTII"
    "i5m8C3s7fhh8RSVUp78XK054ZweW25Xe3tQICF6UuuqMAESfTGfhP591hEikbJTxU"
    "hXfRywjarlwziZyP9waZYu8D0QA7Z84xaDPU1h3kgxb6Gt5DUAdCOg0dMxuiC24gl"
    "nUET9yzHa3bIglZMMxpBiGI+B9jDYjKa03IF1NfsQn8eN1n+JlHyeMXtITrgqQIDAQAB"
)

APP_RSA_PRIVATE_KEY_B64 = (
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDBWM3x7tL1iCDa"
    "PNz6VpARgPVjFJGmnBSXV8SN+lXwIX8q9DkiBNzJRgN7c7v/jX6LseNfZm7ANc86G"
    "GhXLqgPZ781L/5eZRgu31oTOj56turb67GPAr3e3RqQzkL3FkNrgmLQzkgJ9kzHym"
    "3np9MgiLmbwLezt+GHxFJVSnvxcrTnhnB5bbld7e1AgIXpS66owARJ9MZ+E/n3WES"
    "KRslPFSFd9HLCNquXDOJnI/3Bpli7wPRADtnzjFoM9TWHeSDFvoa3kNQB0I6DR0zG"
    "6ILbiCWdQRP3LMdrdsiCVkwzGkGIYj4H2MNiMprTcgXU1+xCfx43Wf4mUfJ4xe0hO"
    "uCpAgMBAAECggEAdMfOnHJDuUmfjjF0xz/BhND/ZfjmgFuFlGPOtHKftYqF5MveNk"
    "35jRhcwhQFWTV9WaL4UobsHexiXhSf8QidObDQLK/wU9N759O/9B0Z38Tb1jll5Zsi"
    "U5n4kb4DdHpd/nGifbwahundNk9uUp1rSBtNAGZGjqZh8j8B+8IhWpOA1090lPiqc"
    "bnCMueSVF3VghNPAYBYE/VpS1zQnkx54FiS/ojvhZNmW9rSnXtci3fiQkLOg2GHI5"
    "ZTIxbFzOVb1F+TTGxtHcwOddOXz6DuaQmysXEmavcw7PrmeibWhc/JggBiBBcYLEU"
    "bnDdYIwnPmP+ymaQfxYUv+wQ/fjvgAQKBgQDqBGY8/pMTngWRnipAS0ciI2to17oo"
    "r1ovutAjMEEHXmHFeKVCh3NFkd0xscUF4wqqkZm8VdRz9QEANlfRgy/CRSPTHGxZc"
    "Bwjwdgr0f946XL5E2RGfNChWjECTSCxxHKktfuIrjDR1bkDIWwYgpGUncnAL8crn+"
    "Iosqlo4YeTSQKBgQDTgl+olhYL6rg3VeiNqbWi30w3+Xn8QOBNBnpKXBxdsUD/CBq"
    "IFyYJnvG3y2yqbNv0JwQijxC7o7VsF72eJYij3zYSufrsU6nIfilMMFpBIy5zJARiG"
    "Eev3ugbIQyE09BIeizxVmOsZ6exJFhej4UipTr7xTOqulmBVtjg8omCYQKBgEcDBL"
    "83hQvr5Ma2Vx3heflrBBnxdIUKCPT43FYBO4pv4n1YydUxYxJWW+fLiPzrU35E5oD"
    "XDrwNObuFwgpKo8Bw2JkkQ+Cz+2YCWYWamMppFMFuV/xnvatowfxvyR8IfL1sl6J3"
    "MUtLbnP7vWCGpoSRiPovxWGAh9FPvcacwVY5AoGAOjvfEo+gKk/JwJKKoNZlCB7q4"
    "U5y450JJKvv56FMvg8bkhwtEeMtueBlNPFxTcsDFEnZvZoeRUthnA09S9mRsWy3ep"
    "hyGbc/O9BglnWJo/2HwHPeMRP2SNnalf2XcMrQwePBlADxGHrBlOgo3IAva8aKYt9"
    "8xjjgg9fhhq3AZoECgYEA14vIL+vdzsvgIMT1mNRqpDOTNEh9STOFPI2qD+UR0GMcP"
    "yoqsMb6ySkgPw+Evrx3W+SZASAFDxTFcIWQ2Ok3ZKzq9nZMNbSerd+lQ7KUmunBOR"
    "VGatuE1etOWIeXl63G05Rz31ElZBxi03g9/FdPp5ImE+NFdpN3pOvjTddv7KM="
)

# 视频观看参数
WATCH_TIME_MIN = 15
WATCH_TIME_MAX = 70
INTEGRAL_INTERVAL = 25  # 领币最小间隔（秒），太短会触发频率限制
INTEGRAL_TYPE = 2  # 看视频赚币类型
MAX_VIDEOS_PER_RUN = 30
MAX_ADD_INTEGRAL_PER_RUN = 150

# 请求参数
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
USER_AGENT_POOL = [
    "Mozilla/5.0 (Linux; Android 16; 2509FPN0BC Build/BP2A.250605.031.A3; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.7339.207 "
    "Mobile Safari/537.36 (Immersed/48.0) Html5Plus/1.0",
    "Mozilla/5.0 (Linux; Android 15; 22101320C Build/TKQ1.221114.001; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/139.0.7296.136 "
    "Mobile Safari/537.36 (Immersed/48.0) Html5Plus/1.0",
    "Mozilla/5.0 (Linux; Android 14; 22081212C Build/TP1A.220624.014; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/139.0.7296.98 "
    "Mobile Safari/537.36 (Immersed/48.0) Html5Plus/1.0",
]

# 线程安全
token_lock = threading.Lock()
print_lock = threading.Lock()
summary_reports = []
summary_lock = threading.Lock()

# ====================================== 【加密模块】 ======================================

class CryptoEngine:
    """芳华未来API加密引擎（逆向自 com.plugin.apisecurity.CryptoUtils）"""

    def __init__(self):
        self.rsa_public_key = None
        self.rsa_private_key = None
        if HAS_CRYPTO:
            try:
                pub_der = base64.b64decode(RSA_PUBLIC_KEY_B64)
                self.rsa_public_key = RSA.import_key(pub_der)
                priv_der = base64.b64decode(APP_RSA_PRIVATE_KEY_B64)
                self.rsa_private_key = RSA.import_key(priv_der)
            except Exception as e:
                print(f"⚠️ RSA密钥加载失败: {e}")

    @staticmethod
    def generate_random_aes_key(length=16):
        """生成随机16位AES密钥（与APP逻辑一致）"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def encrypt_aes(self, plaintext, aes_key):
        """AES/CBC/PKCS5Padding加密，IV=Key"""
        try:
            key_bytes = aes_key.encode('utf-8')
            iv_bytes = aes_key.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            padded = pad(plaintext.encode('utf-8'), AES.block_size)
            encrypted = cipher.encrypt(padded)
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            return None

    def decrypt_aes(self, ciphertext_b64, aes_key):
        """AES/CBC/PKCS5Padding解密，IV=Key"""
        try:
            key_bytes = aes_key.encode('utf-8')
            iv_bytes = aes_key.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted = unpad(cipher.decrypt(base64.b64decode(ciphertext_b64)), AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            return None

    def encrypt_rsa(self, plaintext, public_key=None):
        """RSA/ECB/PKCS1Padding加密"""
        try:
            key = public_key or self.rsa_public_key
            if not key:
                return None
            cipher = PKCS1_v1_5.new(key)
            encrypted = cipher.encrypt(plaintext.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            return None

    def decrypt_rsa(self, ciphertext_b64, private_key=None):
        """RSA/ECB/PKCS1Padding解密"""
        try:
            key = private_key or self.rsa_private_key
            if not key:
                return None
            cipher = PKCS1_v1_5.new(key)
            decrypted = cipher.decrypt(base64.b64decode(ciphertext_b64), None)
            if decrypted:
                return decrypted.decode('utf-8')
            return None
        except Exception as e:
            return None

    def encrypt_request(self, data_dict, timestamp):
        """混合加密请求体（与APP generateHybridCryptoSign一致）
        返回: (encrypted_body_b64, x_api_sign_b64, aes_key)
        """
        if not self.rsa_public_key:
            return None, None, None

        aes_key = self.generate_random_aes_key()
        json_str = json.dumps(data_dict, separators=(',', ':'), ensure_ascii=False) if data_dict else "{}"
        encrypted_body = self.encrypt_aes(json_str, aes_key)
        if not encrypted_body:
            return None, None, None

        sign_str = f"timestamp={timestamp}&aesKey={aes_key}"
        x_api_sign = self.encrypt_rsa(sign_str)
        if not x_api_sign:
            return None, None, None

        return encrypted_body, x_api_sign, aes_key

    def encrypt_get_params(self, params_dict, timestamp):
        """加密GET请求的query参数中的data字段，同时生成签名
        返回: (enc_params_dict, x_api_sign_b64, aes_key)
        """
        if not self.rsa_public_key:
            return params_dict, None, None

        aes_key = self.generate_random_aes_key()
        json_str = json.dumps(params_dict, separators=(',', ':'), ensure_ascii=False)
        encrypted_data = self.encrypt_aes(json_str, aes_key)
        if not encrypted_data:
            return params_dict, None, None

        # GET请求也需要签名，签名串与POST一致
        sign_str = f"timestamp={timestamp}&aesKey={aes_key}"
        x_api_sign = self.encrypt_rsa(sign_str)

        return {"data": encrypted_data}, x_api_sign, aes_key

    def decrypt_response(self, resp_json):
        """解密服务端响应（encryptedKey + encryptedData）"""
        if not isinstance(resp_json, dict):
            return resp_json
        if 'encryptedKey' not in resp_json or 'encryptedData' not in resp_json:
            return resp_json

        enc_key = resp_json.get('encryptedKey', '')
        enc_data = resp_json.get('encryptedData', '')

        if not enc_key or not enc_data or not self.rsa_private_key:
            return resp_json

        aes_key = self.decrypt_rsa(enc_key)
        if not aes_key:
            return resp_json

        plaintext = self.decrypt_aes(enc_data, aes_key)
        if plaintext:
            try:
                return json.loads(plaintext)
            except:
                return resp_json
        return resp_json


# ====================================== 【核心模块】 ======================================

crypto = CryptoEngine()
USE_ENCRYPTION = HAS_CRYPTO and crypto.rsa_public_key is not None

def log(msg, phone=""):
    with print_lock:
        prefix = f"[{phone}] " if phone else ""
        print(f"{prefix}{msg}")


def load_token_cache():
    with token_lock:
        if not os.path.exists(TOKEN_CACHE_FILE):
            return {}
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}


def save_token_cache(cache):
    with token_lock:
        try:
            with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except:
            pass


def derive_device_id(phone):
    """从手机号确定性派生设备ID（同账号永远相同，不同账号永远不同）"""
    return hashlib.md5(f"fhwl_device_{phone}".encode()).hexdigest()


def derive_jpush_id(phone):
    """从手机号确定性派生极光推送ID（模拟真实设备的注册ID）"""
    raw = hashlib.md5(f"fhwl_jpush_{phone}".encode()).hexdigest()
    # 极光registrationId格式：16位hex前缀+4位数字后缀
    return raw[:16] + "0100"


def generate_nonce():
    """生成随机nonce"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))


def build_headers(token="", need_sign=False, aes_key=None, timestamp=None, device_id=None):
    """构建请求头"""
    ua = random.choice(USER_AGENT_POOL)
    headers = {
        "User-Agent": ua,
        "AppPlatform": "android",
        "AppVersion": "1.8.1",
        "AppVersionCode": "1810",
        "AppToken": token,
        "Content-Type": "text/plain" if USE_ENCRYPTION else "application/json;charset=UTF-8",
    }

    if need_sign and USE_ENCRYPTION and timestamp:
        # device_id由调用方传入，确保同账号所有请求一致
        if device_id:
            headers["X-Api-DeviceId"] = device_id
        nonce = generate_nonce()
        headers["X-Api-Nonce"] = nonce
        headers["X-Api-Timestamp"] = str(timestamp)

    return headers


def request_with_retry(session, method, url, rnd, max_retries=MAX_RETRIES, **kwargs):
    """带重试的请求"""
    for attempt in range(max_retries):
        try:
            timeout = rnd.uniform(8, REQUEST_TIMEOUT)
            response = session.request(method, url, timeout=timeout, **kwargs)
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep((2 ** attempt) + rnd.uniform(1, 3))
            else:
                return None
    return None


def api_request(session, method, path, rnd, data=None, params=None, token="", device_id=None):
    """统一API请求入口（自动处理加密/解密）"""
    url = f"{BASE_URL}{path}"
    timestamp = int(time.time() * 1000)

    if USE_ENCRYPTION:
        # 加密模式
        if method == "POST" and data is not None:
            encrypted_body, x_api_sign, aes_key = crypto.encrypt_request(data, timestamp)
            if encrypted_body and x_api_sign:
                headers = build_headers(token, need_sign=True, aes_key=aes_key, timestamp=timestamp, device_id=device_id)
                headers["X-Api-Sign"] = x_api_sign
                resp = request_with_retry(session, "POST", url, rnd, headers=headers, data=encrypted_body)
            else:
                # 加密失败降级为明文
                headers = build_headers(token)
                headers["Content-Type"] = "application/json;charset=UTF-8"
                resp = request_with_retry(session, "POST", url, rnd, headers=headers, json=data)
        elif method == "GET":
            headers = build_headers(token, need_sign=True, timestamp=timestamp, device_id=device_id)
            if params:
                enc_params, x_api_sign, aes_key = crypto.encrypt_get_params(params, timestamp)
                if x_api_sign:
                    headers["X-Api-Sign"] = x_api_sign
                resp = request_with_retry(session, "GET", url, rnd, headers=headers, params=enc_params)
            else:
                resp = request_with_retry(session, "GET", url, rnd, headers=headers)
        else:
            headers = build_headers(token)
            resp = request_with_retry(session, method, url, rnd, headers=headers)
    else:
        # 明文模式
        headers = build_headers(token)
        if method == "POST":
            resp = request_with_retry(session, "POST", url, rnd, headers=headers, json=data)
        elif method == "GET":
            resp = request_with_retry(session, "GET", url, rnd, headers=headers, params=params)
        else:
            resp = request_with_retry(session, method, url, rnd, headers=headers)

    if not resp:
        return None

    try:
        result = resp.json()
        # 自动解密响应
        if USE_ENCRYPTION:
            result = crypto.decrypt_response(result)
        # 调试：非200响应打印错误信息
        if result and isinstance(result, dict) and result.get("code") != 200:
            log(f"API {path} 返回非200: code={result.get('code')}, msg={result.get('msg', '')[:100]}")
        return result
    except Exception as e:
        log(f"API {path} 响应解析失败: {e}, status={resp.status_code}, body={resp.text[:200]}")
        return None


# ====================================== 【任务模块】 ======================================

def login(session, phone, password, rnd, device_id=None):
    """账密登录"""
    jpush_id = derive_jpush_id(phone)
    data = {
        "phone": phone,
        "password": password,
        "jpushId": jpush_id,
        "loginType": 1,
        "source": "yyb"
    }
    result = api_request(session, "POST", "/app/app/login", rnd, data=data, device_id=device_id)
    if result and result.get("code") == 200:
        token = result.get("token", "")
        user_id = result.get("user", {}).get("userId")
        log(f"✅ 登录成功", phone)
        return token, user_id
    else:
        msg = result.get("msg", "未知错误") if result else "请求失败"
        log(f"❌ 登录失败: {msg}", phone)
    return None, None


def verify_token(session, token, rnd, device_id=None):
    """验证Token有效性"""
    result = api_request(session, "GET", "/app/user/getUserInfo", rnd, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("user", {}).get("userId")
    return None


def get_valid_credentials(session, phone, password, rnd, device_id=None):
    """获取有效凭证（优先使用缓存Token）"""
    cache = load_token_cache()
    cached = cache.get(phone, {})
    cached_token = cached.get("token", "")

    if cached_token:
        user_id = verify_token(session, cached_token, rnd, device_id=device_id)
        if user_id:
            log(f"✅ 缓存Token有效", phone)
            return cached_token, user_id
        log(f"⚠️ 缓存Token已失效，重新登录...", phone)

    token, user_id = login(session, phone, password, rnd, device_id=device_id)
    if token and user_id:
        cache[phone] = {"token": token}
        save_token_cache(cache)
    return token, user_id


def daily_sign(session, rnd, token, phone, device_id=None):
    """每日签到"""
    result = api_request(session, "POST", "/app/integral/sign", rnd, data={}, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        msg = result.get("msg", "签到成功")
        log(f"✅ 签到: {msg}", phone)
        return True
    elif result and "已签到" in str(result.get("msg", "")):
        log(f"📌 今日已签到", phone)
        return True
    else:
        log(f"❌ 签到失败: {result}", phone)
    return False


def get_user_info(session, rnd, token, device_id=None):
    """获取用户信息"""
    result = api_request(session, "GET", "/app/user/getUserInfo", rnd, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("user", {})
    return None


def get_user_integral(session, rnd, token, device_id=None):
    """获取用户积分"""
    user = get_user_info(session, rnd, token)
    if user:
        return user.get("integral", 0)
    return None


def get_video_list(session, rnd, token, device_id=None):
    """获取视频列表"""
    params = {"keyword": "", "isRandom": 1, "videoId": "", "pageNum": 1, "pageSize": 10}
    result = api_request(session, "GET", "/app/video/getVideoList-new", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        video_list = result.get("data", {}).get("list", [])
        if not video_list:
            log(f"视频列表为空, data={json.dumps(result.get('data', {}), ensure_ascii=False)[:200]}")
        return video_list
    elif result:
        log(f"获取视频列表失败: code={result.get('code')}, msg={result.get('msg', '')[:100]}")
    else:
        log("获取视频列表: 请求无响应")
    return []


def report_video_event(session, video_id, event, rnd, token, device_id=None):
    """上报视频事件"""
    data = {"videoId": str(video_id), "event": event}
    result = api_request(session, "POST", "/app/video/track", rnd, data=data, token=token, device_id=device_id)
    return result and result.get("code") == 200


def add_integral(session, rnd, token, phone, device_id=None):
    """领取观看积分"""
    data = {"type": INTEGRAL_TYPE}
    result = api_request(session, "POST", "/app/integral/addIntegral", rnd, data=data, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        msg = result.get("msg", "")
        coins = 0
        try:
            import re
            m = re.search(r'(\d+)', msg)
            if m:
                coins = int(m.group(1))
        except:
            pass
        return True, coins
    return False, 0


def get_course_list(session, rnd, token, device_id=None):
    """获取课程列表"""
    params = {"pageNum": 1, "pageSize": 20}
    result = api_request(session, "GET", "/app/course/getCourseList", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("data", {}).get("list", [])
    return []


def get_course_video_list(session, rnd, token, course_id, device_id=None):
    """获取课程视频列表"""
    params = {"courseId": course_id}
    result = api_request(session, "GET", "/app/course/getCourseVideoList", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("data", {}).get("list", [])
    return []


def check_like(session, rnd, token, course_id, device_id=None):
    """检查是否已点赞"""
    params = {"courseId": course_id}
    result = api_request(session, "GET", "/app/course/checkLike", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("isLike", 0) == 1
    return False


def check_favorite(session, rnd, token, course_id, device_id=None):
    """检查是否已收藏"""
    params = {"courseId": course_id}
    result = api_request(session, "GET", "/app/course/checkFavorite", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("isFavorite", 0) == 1
    return False


def check_follow(session, rnd, token, talent_id, device_id=None):
    """检查是否已关注达人"""
    params = {"talentId": talent_id}
    result = api_request(session, "GET", "/app/talent/checkFollow", rnd, params=params, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return result.get("isFollow", 0) == 1
    return False


def like_course(session, rnd, token, course_id, device_id=None):
    """点赞课程"""
    data = {"courseId": course_id}
    result = api_request(session, "POST", "/app/course/like", rnd, data=data, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return True
    return False


def favorite_course(session, rnd, token, course_id, device_id=None):
    """收藏课程"""
    data = {"courseId": course_id}
    result = api_request(session, "POST", "/app/course/favorite", rnd, data=data, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return True
    return False


def follow_talent(session, rnd, token, talent_id, device_id=None):
    """关注达人"""
    data = {"talentId": talent_id}
    result = api_request(session, "POST", "/app/talent/follow", rnd, data=data, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        return True
    return False


def get_invited_reward(session, rnd, token, phone, device_id=None):
    """领取邀请奖励"""
    result = api_request(session, "POST", "/app/invited/getReward", rnd, data={}, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        data = result.get("data", {})
        rewards = data.get("rewardArray", [])
        if rewards:
            log(f"✅ 邀请奖励: {len(rewards)}个奖品", phone)
        return True
    return False


def send_heartbeat(session, rnd, token, device_id=None):
    """发送心跳"""
    data = {"action": "HEARTBEAT"}
    result = api_request(session, "POST", "/app/portrait/heartbeat", rnd, data=data, token=token, device_id=device_id)
    return result and result.get("code") == 200


def create_logs(session, rnd, token, user_id, device_id=None):
    """创建日志"""
    data = {"userId": str(user_id)}
    api_request(session, "POST", "/app/common/createLogs", rnd, data=data, token=token, device_id=device_id)


def get_app_config(session, rnd, token, device_id=None):
    """获取APP配置"""
    api_request(session, "GET", "/app/common/getAppPageConfig", rnd, token=token, device_id=device_id)


def get_sign_status(session, rnd, token, device_id=None):
    """获取签到状态"""
    result = api_request(session, "GET", "/app/integral/getUserSign", rnd, token=token, device_id=device_id)
    if result and result.get("code") == 200:
        is_signed = result.get("isDaySign", False)
        sign_num = result.get("signNum", 0)
        integral = result.get("integral", 0)
        return is_signed, sign_num, integral
    return None, 0, 0


# ====================================== 【主任务流程】 ======================================

def run_single_account(phone, password, rnd):
    """单账号完整任务流程"""
    session = requests.Session()
    # 从手机号派生固定设备ID（同账号永远相同，防风控关键）
    device_id = derive_device_id(phone)

    # 1. 登录
    token, user_id = get_valid_credentials(session, phone, password, rnd, device_id=device_id)
    if not token or not user_id:
        return

    # 2. 初始化
    create_logs(session, rnd, token, user_id, device_id=device_id)
    get_app_config(session, rnd, token, device_id=device_id)

    # 记录初始积分
    initial_integral = get_user_integral(session, rnd, token, device_id=device_id)
    log(f"💰 初始积分: {initial_integral}", phone)

    # 3. 每日签到
    log(f"📋 === 开始签到任务 ===", phone)
    daily_sign(session, rnd, token, phone, device_id=device_id)
    time.sleep(rnd.uniform(2, 5))

    # 查看签到状态
    is_signed, sign_num, sign_integral = get_sign_status(session, rnd, token, device_id=device_id)
    if is_signed is not None:
        log(f"📊 签到状态: 已签{sign_num}天, 当前积分{sign_integral}", phone)
    time.sleep(rnd.uniform(2, 5))

    # 4. 邀请奖励
    log(f"📋 === 邀请奖励 ===", phone)
    get_invited_reward(session, rnd, token, phone, device_id=device_id)
    time.sleep(rnd.uniform(2, 5))

    # 5. 课程点赞/收藏/关注（额外积分来源）
    log(f"📋 === 课程互动任务 ===", phone)
    courses = get_course_list(session, rnd, token, device_id=device_id)
    like_count = 0
    fav_count = 0
    follow_count = 0

    for i, course in enumerate(courses[:5]):  # 只处理前5个课程
        course_id = course.get("courseId")
        if not course_id:
            continue

        # 课程间随机间隔，模拟人工浏览节奏
        if i > 0:
            time.sleep(rnd.uniform(2, 5))

        # 点赞
        if not check_like(session, rnd, token, course_id, device_id=device_id):
            if like_course(session, rnd, token, course_id, device_id=device_id):
                like_count += 1
                log(f"👍 点赞课程: {course.get('courseName', '')[:15]}", phone)
                time.sleep(rnd.uniform(1, 3))

        # 收藏
        if not check_favorite(session, rnd, token, course_id, device_id=device_id):
            if favorite_course(session, rnd, token, course_id, device_id=device_id):
                fav_count += 1
                log(f"⭐ 收藏课程: {course.get('courseName', '')[:15]}", phone)
                time.sleep(rnd.uniform(1, 3))

        # 关注视频发布者（随机跳过，不是每个都关注）
        if rnd.random() < 0.6:
            videos = get_course_video_list(session, rnd, token, course_id, device_id=device_id)
            for video in videos[:2]:
                talent_id = video.get("talentId")
                if talent_id and not check_follow(session, rnd, token, talent_id, device_id=device_id):
                    if follow_talent(session, rnd, token, talent_id, device_id=device_id):
                        follow_count += 1
                        log(f"👀 关注达人ID: {talent_id}", phone)
                        time.sleep(rnd.uniform(1, 3))
                break  # 每个课程只关注一个达人

    if like_count or fav_count or follow_count:
        log(f"📊 互动完成: 点赞{like_count} 收藏{fav_count} 关注{follow_count}", phone)
    time.sleep(rnd.uniform(1, 3))

    # 6. 看视频赚币（核心任务）
    log(f"📋 === 看视频赚币任务 ===", phone)
    total_videos = 0
    total_integral_count = 0
    total_coins_earned = 0
    consecutive_fail = 0

    while total_videos < MAX_VIDEOS_PER_RUN and total_integral_count < MAX_ADD_INTEGRAL_PER_RUN:
        if consecutive_fail >= 5:
            log(f"⚠️ 连续{consecutive_fail}次失败，暂停视频任务", phone)
            break

        video_list = get_video_list(session, rnd, token, device_id=device_id)
        if not video_list:
            log(f"⚠️ 未获取到视频列表，稍后重试", phone)
            time.sleep(rnd.uniform(30, 60))
            consecutive_fail += 1
            continue

        rnd.shuffle(video_list)

        for video in video_list:
            if total_videos >= MAX_VIDEOS_PER_RUN or total_integral_count >= MAX_ADD_INTEGRAL_PER_RUN:
                break

            video_id = video.get("id")
            if not video_id:
                continue

            title = video.get("title", "未知视频")[:20]

            # 上报播放开始
            report_video_event(session, video_id, "PLAY", rnd, token, device_id=device_id)
            time.sleep(rnd.uniform(3, 7))

            # 上报播放3秒
            report_video_event(session, video_id, "PLAY_3S", rnd, token, device_id=device_id)

            # 模拟观看
            watch_time = rnd.uniform(WATCH_TIME_MIN, WATCH_TIME_MAX)

            # 在观看期间定期领币
            elapsed = 0
            last_claim = 0
            rate_limit_backoff = 0  # 频率限制退避计数
            while elapsed < watch_time:
                sleep_time = rnd.uniform(2, 5)
                time.sleep(sleep_time)
                elapsed += sleep_time

                if elapsed - last_claim >= INTEGRAL_INTERVAL + rate_limit_backoff:
                    success, coins = add_integral(session, rnd, token, phone, device_id=device_id)
                    if success:
                        total_integral_count += 1
                        total_coins_earned += coins
                        consecutive_fail = 0
                        rate_limit_backoff = 0  # 成功则重置退避
                    else:
                        consecutive_fail += 1
                        rate_limit_backoff = min(rate_limit_backoff + 10, 60)  # 每次失败多等10秒，上限60
                    last_claim = elapsed

                if total_integral_count >= MAX_ADD_INTEGRAL_PER_RUN:
                    break

            # 上报播放完成
            report_video_event(session, video_id, "COMPLETE", rnd, token, device_id=device_id)
            total_videos += 1
            consecutive_fail = 0

            log(f"🎬 视频完成: {title} | 累计{total_videos}视频 {total_integral_count}次领币 +{total_coins_earned}币", phone)

            # 换视频间隔
            time.sleep(rnd.uniform(5, 15))

            # 每隔一段时间发心跳
            if total_videos % 5 == 0:
                send_heartbeat(session, rnd, token, device_id=device_id)

    # 7. 最终积分查询
    final_integral = get_user_integral(session, rnd, token, device_id=device_id)
    gain = (final_integral - initial_integral) if (final_integral is not None and initial_integral is not None) else 0

    report = (
        f"👤 账号: {phone}\n"
        f"✅ 签到: {'已完成' if is_signed else '未完成'}\n"
        f"🎬 视频: {total_videos}个 | 领币: {total_integral_count}次 | +{total_coins_earned}币\n"
        f"👍 互动: 点赞{like_count} 收藏{fav_count} 关注{follow_count}\n"
        f"💰 初始: {initial_integral} → 最终: {final_integral} | 本次: +{gain}"
    )

    with summary_lock:
        summary_reports.append(report)

    log(f"\n{'='*40}\n{report}\n{'='*40}", phone)

    session.close()


def main():
    print(f"\n{'='*50}")
    print(f"  芳华未来自动化 v1.0")
    print(f"  加密模式: {'✅ 已启用(AES+RSA)' if USE_ENCRYPTION else '⚠️ 明文模式(安装pycryptodome可启用加密)'}")
    print(f"{'='*50}\n")

    env_str = os.environ.get(ENV_VAR_NAME, "")
    if not env_str:
        print(f"❌ 环境变量 {ENV_VAR_NAME} 为空")
        print(f"   格式: FHWL='手机号1#密码1@手机号2#密码2'")
        return

    accounts = []
    for item in env_str.split("@"):
        parts = item.strip().split("#")
        if len(parts) >= 2:
            phone = parts[0].strip()
            pwd = parts[1].strip()
            accounts.append((phone, pwd))

    if not accounts:
        print("❌ 没有解析到有效账号")
        return

    print(f"📋 共解析到 {len(accounts)} 个账号\n")

    threads = []
    for idx, (phone, pwd) in enumerate(accounts, 1):
        thread_random = random.Random(int(time.time() * 1000) + idx)
        # 多账号间隔5-30秒启动，避免同时请求触发风控
        start_delay = thread_random.uniform(5, 30) if len(accounts) > 1 else thread_random.uniform(0, 5)
        log(f"🔄 账号 {phone} 将在 {start_delay:.1f}s 后启动")

        thread = threading.Thread(
            target=run_single_account,
            args=(phone, pwd, thread_random)
        )
        threads.append(thread)
        time.sleep(start_delay)
        thread.start()

    for thread in threads:
        thread.join()

    # 汇总
    if summary_reports:
        print(f"\n{'='*50}")
        print("📋 运行汇总")
        print(f"{'='*50}")
        for report in summary_reports:
            print(f"\n{report}\n")


if __name__ == "__main__":
    main()
