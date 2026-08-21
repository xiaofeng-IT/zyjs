import base64
import hashlib
import hmac
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import os

BASE_URL = "https://yx1534.xiashijie.cn"
USER_AGENT = "okhttp/4.10.0"
VERSION = "1101"

# 读取单个环境变量 JLS 格式 token@deviceid
raw_jls = os.getenv("JLS", "")
if raw_jls and "@" in raw_jls:
    token_str, deviceid_str = raw_jls.split("@", 1)
else:
    token_str = ""
    deviceid_str = ""

CONFIG = {
    "token": token_str,
    "jwtKey1534": os.getenv("JLS_JWTKEY", "2040F49B349C6D39F3A42B0800A45C64"),
    "apkSha1": os.getenv("JLS_APKSHA1", "4B90E168B526835D9700456FC5680AE6FABC56E0"),
    "deviceId": deviceid_str,
    "oaid": os.getenv("JLS_OAID", "92e1c0a430a72e08"),
}

AD_TEMPLATES = [
    {
        "name": "信息流广告",
        "ad_type": "1",
        "dividends": "4",
        "networkId": "16",
        "networkPlacementId": "1209370357806893",
        "placementId": "1209370357806893",
        "type": "4",
    },
    {
        "name": "插屏广告",
        "ad_type": "1",
        "dividends": "4",
        "networkId": "22",
        "networkPlacementId": "104017333",
        "placementId": "104017333",
        "type": "3",
    },
]

TARGET_GOLD = 8000


def b64url(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def jwt_hs256(subject, secret):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(subject)}
    signing_input = ".".join([
        b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
        b64url(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
    ])
    sig = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + b64url(sig)


class JulaishangClient:
    def __init__(self):
        self.token = CONFIG["token"]
        self.jwt_key = CONFIG["jwtKey1534"]
        self.apk_sha1 = CONFIG["apkSha1"].upper()
        self.device_id = CONFIG["deviceId"]
        self.oaid = CONFIG["oaid"]
        self.sha = jwt_hs256(self.apk_sha1, self.jwt_key)
        self.token_a = jwt_hs256(self.token, self.jwt_key)

    def _headers(self, *, sha_header=None, token_a=False):
        h = {"user-agent": USER_AGENT, "version": VERSION, "token": self.token}
        if token_a and self.token_a:
            h["tokenA"] = self.token_a
        if sha_header and self.sha:
            h[sha_header] = self.sha
        return h

    def _request(self, method, path, data=None, *, sha_header=None, token_a=False):
        headers = self._headers(sha_header=sha_header, token_a=token_a)
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["content-type"] = "application/x-www-form-urlencoded"
        url = BASE_URL + path
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            return {"code": 0, "msg": f"请求失败：{exc.reason}"}
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"code": 0, "msg": text}

    def get_forecast_gold(self):
        data = self._request("GET", "/api/Member/GetUserinfo", sha_header="sha", token_a=True)
        user = ((data.get("data") or {}).get("userinfo") or {})
        gold = user.get("forecast_gold")
        try:
            return int(gold) if gold is not None else None
        except (ValueError, TypeError):
            return None

    def get_userinfo_brief(self):
        data = self._request("GET", "/api/Member/GetUserinfo", sha_header="sha", token_a=True)
        user = ((data.get("data") or {}).get("userinfo") or {})
        mobile = str(user.get("mobile") or "")
        if len(mobile) >= 7:
            mobile = mobile[:3] + "****" + mobile[-4:]
        return {
            "mobile": mobile,
            "nickname": user.get("nickname", "-"),
            "gold": user.get("gold", "-"),
            "forecast": user.get("forecast_gold", "-"),
        }

    def submit_report(self, template):
        report = dict(template)
        name = report.pop("name")
        report["deviceId"] = self.device_id
        report["oaid"] = self.oaid
        report["sha"] = self.sha
        report["loadId"] = str(uuid.uuid4())
        report["eCPM"] = str(random.randint(6000, 8000))
        report["version"] = VERSION
        compact_json = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        signed = {
            "deviceId": self.device_id,
            "oaid": self.oaid,
            "sgin": jwt_hs256(compact_json, self.jwt_key),
            "tc": self.sha,
            "ta": jwt_hs256("AOterUrl", self.jwt_key),
            "tb": jwt_hs256(compact_json, self.jwt_key),
        }
        result = self._request("POST", "/api/Pubqingqiu/Pdefgfuxdob", signed)
        return name, result


def main():
    if not CONFIG["token"] or not CONFIG["deviceId"]:
        print("❌ 环境变量 JLS 未配置，请填写：token@deviceid")
        return

    client = JulaishangClient()
    print("=== 剧来赏自动上报 ===")
    info = client.get_userinfo_brief()
    print(f"用户：{info['mobile']} / {info['nickname']}")
    print(f"金币：{info['gold']}，预估金币：{info['forecast']}")
    print(f"目标：{TARGET_GOLD}\n")

    count = 0
    while True:
        forecast = client.get_forecast_gold()
        if forecast is None:
            print("无法获取预估金币，退出")
            break
        print(f"[第{count}次] 预估金币：{forecast} / 目标：{TARGET_GOLD}")
        if forecast >= TARGET_GOLD:
            print(f"\n预估金币已达 {forecast}，停止上报")
            info = client.get_userinfo_brief()
            print(f"用户：{info['mobile']} / {info['nickname']}")
            print(f"金币：{info['gold']}，预估金币：{info['forecast']}")
            break

        template = random.choice(AD_TEMPLATES)
        name, result = client.submit_report(template)
        count += 1
        msg = result.get("msg") or result
        print(f"- 上报 {name}：{msg}")

        if result.get("code") != 1:
            print("上报失败，退出")
            break

        wait = random.randint(25, 30)
        print(f"- 等待 {wait} 秒...\n")
        time.sleep(wait)


if __name__ == "__main__":
    main()