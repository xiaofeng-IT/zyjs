import base64
import io
import json
import logging
import random
import re
import os
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import sys
import time
from urllib.parse import urlencode

from curl_cffi import requests
import ddddocr

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ============ 配置 ============
API_HOST = "http://103.217.203.96:5645"
WEB_HOST = "http://103.217.203.96:9585"
REQUEST_TIMEOUT = 20
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAp0KW/emsWnZgDFDDKF7q
SfE9uK1sKvlYNLLtUt/tjV79/Uz9CSuBbWhOyHUi7sX8V4Wmg8Cg0LK+/BDxCGMh
7SQfbI+ZsKJqaW/cSL4vrItePXIuam/+WgeNG4Q2M+1cYCqEotwBvAWVmoZrr1id
Am8QjKbZYVOikfogaSySBWwER9cy6nHCWnSZtBJql1npvXPLc5L5D0PCg7DoKGNE
euA/RTMoffizPN4R950Ob8gG3x3w7kV65JDwnIrhhdoLuhT/9QmV65hVmbAodMIX
DN8UkNJRFkSQReK7GhNYY5+wu47mIW2JfVZMkiOcwL9Oz3irudVj4SdD8wcAOxTu
gQIDAQAB
-----END PUBLIC KEY-----"""
BONUS_SECRET = "bC71D2d74A614d220C16542B04042cF8"

# ============ Session ============
session = requests.Session(impersonate="chrome110")
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; PHM110 Build/RKQ1.211119.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.129 Mobile Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh-HK;q=0.9,zh;q=0.8",
    "Accept-Encoding": "gzip, deflate",
})

ocr = ddddocr.DdddOcr(show_ad=False)
rsa_key = RSA.import_key(RSA_PUBLIC_KEY)
rsa_cipher = PKCS1_v1_5.new(rsa_key)


def random_delay(min_s=0.5, max_s=2.0):
    time.sleep(random.uniform(min_s, max_s))


def api_get(path, headers=None, **kwargs):
    url = API_HOST + path
    h = headers or {}
    return session.get(url, headers=h, timeout=REQUEST_TIMEOUT, **kwargs)


def api_post(path, json_body=None, headers=None, **kwargs):
    url = API_HOST + path
    h = headers or {}
    h.setdefault("Content-Type", "application/json")
    return session.post(url, json=json_body, headers=h, timeout=REQUEST_TIMEOUT, **kwargs)


def api_put(path, json_body=None, headers=None, **kwargs):
    url = API_HOST + path
    h = headers or {}
    h.setdefault("Content-Type", "application/json")
    return session.put(url, json=json_body, headers=h, timeout=REQUEST_TIMEOUT, **kwargs)


def call_ok(resp, expected_code=1):
    try:
        data = resp.json()
        return data.get("code") == expected_code, data
    except Exception:
        return False, {"raw": resp.text[:300]}


# ============ 第一步：获取验证码 ============
def get_captcha():
    """获取注册验证码, 返回 (captcha_key, captcha_code)"""
    log.info("获取注册验证码...")
    resp = api_get("//api/login/captcha", headers={
        "Origin": WEB_HOST,
        "X-Requested-With": "mark.via",
        "Referer": WEB_HOST + "/",
    })
    ok, data = call_ok(resp)
    if not ok:
        log.error(f"获取验证码失败: {resp.status_code} {resp.text[:200]}")
        return None, None

    captcha_key = data["data"]["captchaKey"]
    b64_data = data["data"]["captchaBase64"]
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_data)

    code = ocr.classification(img_bytes).strip()
    log.info(f"验证码Key: {captcha_key}, OCR结果: {code}")
    return captcha_key, code


# ============ 第二步：注册 ============
def register(mobile, password, referee="MjYwODM2"):
    captcha_key, captcha_code = get_captcha()
    if not captcha_key or not captcha_code:
        return False

    log.info(f"注册账号: {mobile}")
    body = {
        "referee": referee,
        "mobile": mobile,
        "password": password,
        "captchaKey": captcha_key,
        "captchaCode": captcha_code,
    }

    try:
        session.options(API_HOST + "//api/login/register", headers={
            "Origin": WEB_HOST,
            "X-Requested-With": "mark.via",
            "Referer": WEB_HOST + "/",
        }, timeout=10)
    except Exception:
        pass
    random_delay()

    resp = api_post("//api/login/register", json_body=body, headers={
        "Origin": WEB_HOST,
        "X-Requested-With": "mark.via",
        "Referer": WEB_HOST + "/",
    })
    ok, data = call_ok(resp)
    if ok:
        log.info(f"注册成功: {extract_msg(data)}")
        return True
    else:
        log.error(f"注册失败: {resp.status_code} {resp.text[:300]}")
        return False


# ============ 第三步：登录 ============
def login(mobile, password):
    log.info(f"登录账号: {mobile}")
    body = {"account": mobile, "password": password}
    resp = api_post("//api/login", json_body=body, headers={
        "Api-Type": "android",
    })
    ok, data = call_ok(resp)
    if ok:
        token = data["data"]["token"]
        log.info(f"登录成功, token: {token[:20]}...")
        return token, data["data"]
    else:
        log.error(f"登录失败: {resp.status_code} {resp.text[:300]}")
        return None, None


# ============ 第四步：获取用户信息 ============
def get_member(token):
    resp = api_get("//api/member", headers={"token": token})
    ok, data = call_ok(resp)
    if ok:
        d = data["data"]
        log.info(f"用户: {d.get('nickName', '')}, 金币: {d.get('jinbi')}, "
                 f"今日任务: {d.get('todayTask')}, 等级: {d.get('levelName', '')}")
        return d
    log.error(f"获取用户信息失败: {resp.text[:200]}")
    return None


# ============ 第五步：获取任务列表 ============
def get_product_list(token):
    resp = api_get("//api/product?tid=1", headers={"token": token})
    ok, data = call_ok(resp)
    if ok and data.get("data"):
        products = data["data"]
        log.info(f"获取到 {len(products)} 个任务")
        return products
    log.error(f"获取任务列表失败: {resp.text[:200]}")
    return []


# ============ 第六步：完成任务 ============
def _calc_bonus_str(timestamp_ms, user_id, product_video_id):
    """
    生成 bonusStr
    签名原文: "date=" + timestamp + "&userId=" + user_id + "2026" + "&videoId=" + product_video_id + BONUS_SECRET
    MD5 -> RSA 加密 -> Base64
    """
    raw = "date=" + str(timestamp_ms) + "&userId=" + str(user_id) + "2026&videoId=" + str(
        product_video_id) + BONUS_SECRET
    md5_hex = hashlib.md5(raw.encode("utf-8")).hexdigest()
    encrypted = rsa_cipher.encrypt(md5_hex.encode("utf-8"))
    bonus_str = base64.b64encode(encrypted).decode("ascii")
    log.info("生成 bonusStr: userId=%s, videoId=%s, md5=%s...", user_id, product_video_id, md5_hex[:16])
    return bonus_str


def complete_task(token, user_id, product):
    date_time = int(time.time() * 1000)
    product_id = product["id"]
    product_video_id = product["videoId"]
    bonus_str = _calc_bonus_str(date_time, user_id, product_video_id)
    body = {"bonusStr": bonus_str, "videoId": product_id, "dateTime": date_time}
    resp = api_post("//api/index/taskBonus", json_body=body, headers={"token": token})
    ok, data = call_ok(resp)
    if ok:
        log.info("任务提交成功: %s", extract_msg(data))
        return True, data
    else:
        log.warning("任务提交失败: %s", resp.text[:250])
        return False, data


# ============ 第七步：绑定支付宝 ============
def bind_alipay(token, truename, zhifubao):
    log.info(f"校验提现信息: {truename} / {zhifubao[:3]}***")
    body = {"truename": truename, "zhifubao": zhifubao}
    resp = api_post("//api/withdrawal/check", json_body=body, headers={"token": token})
    ok, data = call_ok(resp)
    if ok:
        log.info(f"校验通过: {extract_msg(data)}")
    else:
        log.warning(f"校验失败: {resp.text[:200]}")

    random_delay()

    resp = api_put("//api/member", json_body=body, headers={"token": token})
    ok, data = call_ok(resp)
    if ok:
        log.info(f"提现信息绑定成功: {extract_msg(data)}")
        return True
    else:
        log.error(f"绑定失败: {resp.text[:200]}")
        return False


# ============ 第八步：提现 ============
def withdraw(token, money="0.1"):
    log.info(f"发起提现: {money} 元")
    body = {"money": money}
    resp = api_post("//api/withdrawal/add", json_body=body, headers={"token": token})
    try:
        data = resp.json()
        ok = data.get("code") == 1
        log.info(f"提现结果: code={data.get('code')}, msg={data.get('msg', '')}")
        return ok, data
    except Exception:
        log.info(f"提现请求已发送, HTTP {resp.status_code}, 响应: {resp.text[:200]}")
        return True, {"raw": resp.text[:200]}


def extract_msg(data):
    return data.get("msg", "无消息")


# ============ 主流程 ============
def main():
    print("=" * 50)
    print("酷漫传媒 自动化脚本")
    print("=" * 50)

    # 优先从环境变量读取（青龙面板）
    # 环境变量 kmcm 格式: 手机号#密码#姓名#支付宝
    env_val = os.environ.get("kmcm", "")
    if env_val:
        parts = env_val.split("#")
        if len(parts) >= 4:
            mobile = parts[0].strip()
            password = parts[1].strip()
            truename = parts[2].strip()
            zhifubao = parts[3].strip()
            log.info("从环境变量 kmcm 读取配置")
        else:
            log.error("环境变量 kmcm 格式错误，需要: 手机号#密码#姓名#支付宝")
            return
    else:
        mobile = input("请输入手机号: ").strip()
        password = input("请输入密码: ").strip()
        truename = input("请输入提现真实姓名: ").strip()
        zhifubao = input("请输入支付宝账号(手机号/邮箱): ").strip()

    if len(sys.argv) >= 3:
        mobile = sys.argv[1]
        password = sys.argv[2]
    if len(sys.argv) >= 5:
        truename = sys.argv[3]
        zhifubao = sys.argv[4]

    log.info(f"手机号: {mobile}, 姓名: {truename}")

    # 预热 OCR
    # OCR 首次调用会在 get_captcha 中自动预热，这里跳过

    # Step 1: 注册
    log.info("=== 步骤1: 注册 ===")
    success = register(mobile, password)
    if not success:
        log.warning("注册可能已存在账号, 继续尝试登录...")
    random_delay()

    # Step 2: 登录
    log.info("=== 步骤2: 登录 ===")
    token, user_data = login(mobile, password)
    if not token:
        log.error("登录失败, 退出")
        return
    random_delay()

    # Step 3: 查看用户信息
    log.info("=== 步骤3: 用户信息 ===")
    member = get_member(token)
    if member:
        gold = member.get("jinbi", 0)
        log.info(f"当前金币: {gold}")
    random_delay()

    # Step 4: 获取任务列表
    log.info("=== 步骤4: 任务列表 ===")
    products = get_product_list(token)
    if not products:
        log.warning("未获取到任务, 跳过完成任务步骤")
    else:
        log.info("=== 步骤5: 完成任务 ===")
        p = products[0]
        pid = p["id"]
        log.info(f"尝试完成任务: id={pid}, title={p.get('title', '')[:30]}...")
        task_ok, _ = complete_task(token, user_data.get("id"), p)

        if task_ok:
            random_delay()
            member = get_member(token)
            if member:
                gold = member.get("jinbi", 0)
                log.info(f"任务后金币: {gold}")
        else:
            log.warning("任务提交失败, 继续提现流程...")

    random_delay()

    # Step 6: 绑定支付宝
    log.info("=== 步骤6: 绑定提现信息 ===")
    bind_alipay(token, truename, zhifubao)
    random_delay()

    # Step 7: 提现
    log.info("=== 步骤7: 发起提现 ===")
    withdraw_ok, _ = withdraw(token, "0.1")

    # 最后再看余额
    random_delay()
    member = get_member(token)
    if member:
        log.info(f"最终金币: {member.get('jinbi')}, 冻结金币: {member.get('frozenJinbi')}")

    log.info("流程完成!")


if __name__ == "__main__":
    main()
