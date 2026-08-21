# 天翼云盘自动签到 Python 版

import time
import os
import base64
import rsa
import requests
import re
from urllib.parse import urlparse, parse_qs

# 尝试导入青龙面板自带的 notify 推送模块
try:
    from notify import send
except ImportError:
    print("⚠️ 提醒：未找到青龙面板的 notify.py 推送模块，将只在日志中输出，不发送推送。")
    def send(title, msg):
        pass

BI_RM = list("0123456789abcdefghijklmnopqrstuvwxyz")
B64MAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

# ================= 变量配置区 =================
# 从环境变量获取账号信息 (青龙面板专用)
ty_usernames = os.getenv("ty_username").split('&') if os.getenv("ty_username") else []
ty_passwords = os.getenv("ty_password").split('&') if os.getenv("ty_password") else []
# ============================================

# 检查环境变量
if not ty_usernames or not ty_passwords:
    print("❌ 严重错误：未找到账号密码信息！")
    print("请去青龙面板的【环境变量】中添加 ty_username 和 ty_password")
    exit(1)

accounts = [{"username": u, "password": p} for u, p in zip(ty_usernames, ty_passwords)]

def mask_phone(phone):
    """仅显示手机号后四位"""
    return phone[-4:] if len(phone) >= 4 else phone

def int2char(a):
    return BI_RM[a]

def b64tohex(a):
    d = ""
    e = 0
    c = 0
    for i in range(len(a)):
        if list(a)[i] != "=":
            v = B64MAP.index(list(a)[i])
            if 0 == e:
                e = 1
                d += int2char(v >> 2)
                c = 3 & v
            elif 1 == e:
                e = 2
                d += int2char(c << 2 | v >> 4)
                c = 15 & v
            elif 2 == e:
                e = 3
                d += int2char(c)
                d += int2char(v >> 2)
                c = 3 & v
            else:
                e = 0
                d += int2char(c << 2 | v >> 4)
                d += int2char(15 & v)
    if e == 1:
        d += int2char(c << 2)
    return d

def rsa_encode(j_rsakey, string):
    rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
    return b64tohex((base64.b64encode(rsa.encrypt(f'{string}'.encode(), pubkey))).decode())

def login(username, password):
    print("🔄 正在执行登录流程...")
    s = requests.Session()
    try:
        urlToken = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
        r = s.get(urlToken)
        match = re.search(r"href\s*=\s*'([^']*autoLogin[^']*)'", r.text)
        if not match:
            print("❌ 错误：未找到动态登录页")
            return None

        auto_login_url = match.group(1)
        r = s.get(auto_login_url, allow_redirects=True)
        redirect_url = r.url  

        parsed = urlparse(r.url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        r = s.post("https://open.e.189.cn/api/logbox/oauth2/wap/appConf.do", params=params, timeout=10)
        conf = r.json()
        if conf.get('result', '-1') != '0':
            print(f"❌ 错误：获取登录配置失败 - {conf.get('msg', '未知错误')}")
            return None

        data = conf['data']
        lt = data['lt']
        returnUrl = data['returnUrl']
        paramId = data['paramId']
        accountType = data.get('accountType', '02')
        s.headers.update({"lt": lt})

        login_html_url = re.sub(r'/index\.html', '/login.html', redirect_url)
        r = s.get(login_html_url, timeout=10)
        match = re.search(r'id="j_rsaKey"\s+value="([^"]+)"', r.text)
        if not match:
            print("❌ 错误：获取RSA密钥失败")
            return None
        j_rsakey = match.group(1)

        username_enc = rsa_encode(j_rsakey, username)
        password_enc = rsa_encode(j_rsakey, password)

        data = {
            "appKey": "cloud",
            "accountType": accountType,
            "userName": f"{{RSA}}{username_enc}",
            "password": f"{{RSA}}{password_enc}",
            "validateCode": "",
            "captchaToken": "",
            "returnUrl": returnUrl,
            "mailSuffix": "@189.cn",
            "paramId": paramId
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0',
            'Referer': 'https://open.e.189.cn/',
        }

        r = s.post(
            "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do",
            data=data,
            headers=headers,
            timeout=10
        )

        result = r.json()
        if str(result.get('result', -1)) != '0':
            print(f"❌ 登录错误：{result.get('msg', '未知错误')}")
            return None

        if 'toUrl' not in result:
            print("❌ 错误：登录响应缺少 toUrl")
            return None
        s.get(result['toUrl'])

        print("✅ 登录成功")
        return s

    except Exception as e:
        print(f"⚠️ 登录异常：{str(e)}")
        return None

def main():
    print("\n=============== 天翼云盘签到开始 ===============")
    all_results = []

    for acc in accounts:
        username = acc["username"]
        password = acc["password"]
        masked_phone = mask_phone(username)
        account_result = {"tail": masked_phone, "status": "", "result": ""}

        print(f"\n🔔 处理账号：{masked_phone}")

        session = login(username, password)
        if not session:
            account_result["status"] = "❌"
            account_result["result"] = "登录失败"
            all_results.append(account_result)
            continue

        try:
            rand = str(round(time.time() * 1000))
            sign_url = f'https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
                "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                "Host": "m.cloud.189.cn",
            }
            resp = session.get(sign_url, headers=headers).json()
            if str(resp.get('isSign')).lower() == "false" or resp.get('isSign') is False:
                account_result["status"] = "✅"
                account_result["result"] = f"+{resp.get('netdiskBonus', '?')}M"
            else:
                account_result["status"] = "✅"
                account_result["result"] = f"已签到 +{resp.get('netdiskBonus', '?')}M"

        except Exception as e:
            account_result["status"] = "❌"
            account_result["result"] = "签到异常"

        all_results.append(account_result)
        print(f"  {account_result['status']} | {account_result['result']}")

    # 生成推送消息文本
    msg_lines = []
    for res in all_results:
        msg_lines.append(f"账号尾号 {res['tail']} | {res['status']} | {res['result']}")
    msg = "\n".join(msg_lines)

    # 触发通用推送（PushPlus / Server酱 / Bark等）
    send("天翼云盘签到通知", msg)
    print("\n✅ 所有账号处理完成！")

if __name__ == "__main__":
    main()

