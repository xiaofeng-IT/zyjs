#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONE 自动购买历史点播脚本
APP下载链接：https://75x8yg27.cyou?code=Mrw1MmaFuU
创建日期：2024-11-27
说明：访问https://onelogin.316199.xyz/ 登录账号（未注册也可直接登录）并获取config.json配置文件，将下载下来的config.json配置文件保存到脚本同级目录
"""

import base64
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from SendNotify import capture_output
except Exception as exc:
    print(f"[警告] 通知模块 SendNotify.py 导入失败：{exc}，将跳过通知推送。")

    def capture_output(title: str = "脚本运行结果"):
        def decorator(func):
            return func

        return decorator


def _load_optional_proxy_module() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proxy_path = os.path.join(script_dir, "LoadProxy.py")
    if not os.path.exists(proxy_path):
        return

    try:
        spec = importlib.util.spec_from_file_location("LoadProxy", proxy_path)
        if spec is None or spec.loader is None:
            print("[警告] 代理模块加载失败：无法创建模块规格，将通过直连发起请求。")
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules["LoadProxy"] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"[警告] 代理模块导入失败：{exc}，将通过直连发起请求。")


_load_optional_proxy_module()

import requests

ONE_CONFIG = {
    "API_URL": "https://api.apubis.com/v2.5/bootstrap",
    "PLATFORM": "2",
    "APP_VERSION": "2.6.1.2",
    "buy_url": "https://api.a9a2bc4.com",
    "end_month": "2021-9",
}

ONE_AES_KEY = b"l*bv%Ziq000Biaog"
ONE_AES_IV = b"8597506002939240"
ONE_SIGN_SECRET = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
ONE_IP = "0.0.0.0"
REQUEST_TIMEOUT = 30

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(CURRENT_DIR, "config.json")


def read_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def write_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)


def clean_empty_accounts(config):
    if "accounts" not in config or not isinstance(config["accounts"], list):
        return config

    original_count = len(config["accounts"])
    config["accounts"] = [
        account for account in config["accounts"]
        if account.get("TOKEN") and account.get("USER_KEY")
    ]

    removed_count = original_count - len(config["accounts"])
    if removed_count > 0:
        print(f"已清理 {removed_count} 个空账号")
        write_config(config)

    return config


def check_config():
    if not os.path.exists(CONFIG_PATH):
        print("=" * 30)
        print("❌ 未找到配置文件 config.json")
        print("")
        print("📱 请使用浏览器访问以下网址登录并获取配置文件：")
        print("🔗 https://onelogin.316199.xyz")
        print("")
        print("下载配置文件后，将其放在脚本同级目录下")
        print("=" * 30)
        return False

    try:
        config = clean_empty_accounts(read_config())

        if not config.get("accounts"):
            print("配置文件中缺少账号信息，请至少配置一个账号")
            return False

        common_fields = ["API_URL", "APP_VERSION", "PLATFORM"]
        missing_common_fields = [field for field in common_fields if not config.get(field)]
        if missing_common_fields:
            print(f"配置文件缺少以下共用配置项: {', '.join(missing_common_fields)}")
            print("请在配置文件中填入这些信息")
            return False

        required_account_fields = ["TOKEN", "USER_KEY"]
        for index, account in enumerate(config["accounts"], 1):
            missing_fields = [field for field in required_account_fields if not account.get(field)]
            if missing_fields:
                print(f"账号 {index} 缺少以下必要项: {', '.join(missing_fields)}")
                print("请在配置文件中填入这些信息后再运行脚本")
                return False

        return True
    except Exception as exc:
        print(f"读取配置文件时出错: {exc}")
        return False


def get_previous_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def remove_pkcs7_padding(data):
    if not data:
        return data

    padding_length = data[-1]
    if padding_length > AES.block_size or padding_length > len(data):
        return data

    if data[-padding_length:] != bytes([padding_length]) * padding_length:
        return data

    return data[:-padding_length]


def one_aes_encrypt(data):
    # service.js 先手动 PKCS#7，再交给 WebCrypto AES-CBC；WebCrypto 会再补一层 padding。
    data_bytes = data.encode("utf-8")
    manually_padded = pad(data_bytes, AES.block_size)
    webcrypto_padded = pad(manually_padded, AES.block_size)
    encrypted = AES.new(ONE_AES_KEY, AES.MODE_CBC, ONE_AES_IV).encrypt(webcrypto_padded)
    return base64.b64encode(encrypted).decode("utf-8")


def one_aes_decrypt(encrypted_data):
    encrypted_bytes = base64.b64decode(encrypted_data)
    decrypted = AES.new(ONE_AES_KEY, AES.MODE_CBC, ONE_AES_IV).decrypt(encrypted_bytes)

    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        pass

    decrypted = remove_pkcs7_padding(decrypted)
    return decrypted.decode("utf-8")


def md5_hash(data):
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def parse_uuid_from_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("无效的JWT格式")

        payload = parts[1].replace("-", "+").replace("_", "/")
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded_payload = json.loads(base64.b64decode(payload).decode("utf-8"))

        uuid = decoded_payload.get("uuid")
        if not uuid:
            raise ValueError("Token中未找到UUID字段")

        return uuid
    except Exception as e:
        raise ValueError(f"Token解析失败: {e}")


def generate_one_sign(ip, timestamp, user_key, uuid, platform):
    sign_str = f"{ip}.{platform}.{timestamp}.{user_key}.{uuid}"
    first_hash = md5_hash(sign_str)
    return md5_hash(first_hash + ONE_SIGN_SECRET)


def request_one_api(url, payload, headers):
    encrypted_payload = one_aes_encrypt(payload)
    response = requests.post(url, headers=headers, data=encrypted_payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    decrypted_response = one_aes_decrypt(response.text)
    return json.loads(decrypted_response)


def build_refresh_headers(token, user_key, uuid, timestamp, sign, app_version, platform):
    return {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "UUID": uuid,
        "User-Key": user_key,
        "Accept": "application/json text/plain */*",
        "App-Version": app_version,
        "Timestamp": timestamp,
        "App_Version": app_version,
        "Accept-Language": "zh-CNzh-Hans;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Platform": platform,
        "Token": token,
        "IP": ONE_IP,
        "User-Agent": "Decryptchatr/2 CFNetwork/3826.400.120 Darwin/24.3.0",
        "Sign": sign,
        "Cookie": "X-SUDUN-WAF-R-C=0001690393",
    }


def build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform):
    return {
        "content-type": "application/x-www-form-urlencoded;charset=utf-8",
        "uuid": uuid,
        "user-key": user_key,
        "accept": "application/json, text/plain, */*",
        "app-version": app_version,
        "timestamp": timestamp,
        "app_version": app_version,
        "accept-language": "zh-CN,zh-Hans;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "platform": platform,
        "token": token,
        "ip": ONE_IP,
        "user-agent": "PullUpTag/1 CFNetwork/1474 Darwin/23.0.0",
        "cookie": "X-SUDUN-WAF-R-C=0001690476",
        "sign": sign,
    }


def build_one_context(account, config):
    token = account["TOKEN"]
    user_key = account["USER_KEY"]
    platform = str(config.get("PLATFORM", "2"))
    uuid = parse_uuid_from_token(token)
    timestamp = str(int(time.time()))
    sign = generate_one_sign(ONE_IP, timestamp, user_key, uuid, platform)
    return token, user_key, uuid, timestamp, sign, platform


def refresh_token_local(account, config):
    try:
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config["APP_VERSION"])

        payload = (
            f"channel_code=&timestamp={timestamp}&token={token}&uuid={uuid}"
            f"&app-version={app_version}&app_version={app_version}&user-key={user_key}"
            f"&platform={platform}&ip={ONE_IP}&sign={sign}"
        )
        headers = build_refresh_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(config["API_URL"], payload, headers)

        if data.get("code") == 200:
            user_data = data["data"]["user"]
            new_token = user_data.get("token")
            if not new_token:
                return False, "Token为空，请重新获取账号配置"
            account["TOKEN"] = new_token
            account["nickname"] = user_data.get("nickname", account.get("nickname", ""))
            account["avatar"] = user_data.get("avatar", account.get("avatar", ""))
            account["integral"] = user_data.get("integral", account.get("integral", 0))
            account["login_ip"] = user_data.get("login_ip", account.get("login_ip", ""))
            account["updated_at"] = user_data.get("updated_at", account.get("updated_at", ""))
            return True, "Token更新成功"
        return False, f"请求失败: {data.get('mezsage', data.get('message', '未知错误'))}"
    except Exception as e:
        return False, f"刷新Token失败: {e}"


def get_article_list_local(account, config, published_at, page=1):
    try:
        buy_url = config.get("buy_url", "https://api.zbdk8ws.com")
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config["APP_VERSION"])
        page_size = 20

        payload = (
            f"published_at={published_at}&model_id=6&page={page}&size={page_size}"
            f"&sort=published_at&buy_type=0&timestamp={timestamp}&token={token}&uuid={uuid}"
            f"&app-version={app_version}&app_version={app_version}&user-key={user_key}"
            f"&platform={platform}&ip={ONE_IP}&sign={sign}"
        )
        headers = build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(f"{buy_url.rstrip('/')}/v2.5/article/discovery", payload, headers)
        return True, data
    except Exception as e:
        return False, str(e)


def purchase_item_local(account, config, item_id):
    try:
        buy_url = config.get("buy_url", "https://api.zbdk8ws.com")
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config["APP_VERSION"])

        payload = (
            f"id={item_id}&timestamp={timestamp}&token={token}&uuid={uuid}"
            f"&app-version={app_version}&app_version={app_version}&user-key={user_key}"
            f"&platform={platform}&ip={ONE_IP}&sign={sign}"
        )
        headers = build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(f"{buy_url.rstrip('/')}/v2.5/purchase/buy", payload, headers)
        return True, data
    except Exception as e:
        return False, str(e)


def parse_end_month(config):
    end_month_config = config.get("end_month", "2021-9")
    try:
        end_year, end_month = map(int, str(end_month_config).split("-"))
        print(f"将扫描点播列表直到 {end_year}年{end_month}月,可通过编辑config.json指定")
        return end_year, end_month
    except Exception:
        print("扫描结束月份配置有误，将使用默认值: 2021年9月")
        return 2021, 9


def run_task():
    if not check_config():
        return 1

    config = clean_empty_accounts(read_config())
    for key, value in ONE_CONFIG.items():
        config.setdefault(key, value)

    accounts = config["accounts"]
    end_year, end_month = parse_end_month(config)
    current_year, current_month = datetime.now().year, datetime.now().month

    print("\n====== ONE补充历史0元点播脚本开始执行 ======")
    print(f"共有 {len(accounts)} 个账号配置")
    print("脚本作者:3iXi,版本:V10,更新时间:26/05/22")
    print("https://github.com/3ixi")
    print("本脚本免费使用,让你付费的均是骗子")

    total_purchase_count = 0

    for account_idx, account in enumerate(accounts):
        account_name = account.get("nickname", f"账号{account_idx + 1}")
        print(f"\n开始为 {account_name} 执行白嫖操作...")

        success, message = refresh_token_local(account, config)
        if success:
            print(f"{account_name} Token刷新成功")
            config["accounts"][account_idx] = account
            write_config(config)
        else:
            print(f"❌ {account_name} Token刷新失败: {message}")
            continue

        scan_year, scan_month = current_year, current_month
        while (scan_year > end_year) or (scan_year == end_year and scan_month >= end_month):
            published_at = f"20;{scan_year - 2020}-{scan_month}"
            print(f"{account_name}: 开始扫描 {scan_year}年{scan_month}月 的数据...")

            page = 1
            has_data = True
            month_purchase_count = 0

            while page <= 60 and has_data:
                success, data = get_article_list_local(account, config, published_at, page)
                if not success:
                    print(f"❌ {account_name}: {scan_year}年{scan_month}月 第 {page} 页请求失败: {data}")
                    break

                if not data.get("data"):
                    has_data = False
                    break

                buyable_items = [
                    item for item in data["data"]
                    if item.get("buy") == 0 and str(item.get("coin")) == "0"
                ]

                for item in buyable_items:
                    buy_id = item.get("id")
                    buy_title = item.get("title", "")
                    success, buy_data = purchase_item_local(account, config, buy_id)
                    if success:
                        result = buy_data.get("mezsage", buy_data.get("message", "未知"))
                        print(f"✅ {account_name}: 购买成功 - {buy_title} ({result})")
                        month_purchase_count += 1
                        total_purchase_count += 1
                    else:
                        print(f"❌ {account_name}: 购买失败 - {buy_title} ({buy_data})")

                if len(data["data"]) < 20:
                    break
                page += 1

            if month_purchase_count > 0:
                print(f"📊 {account_name}: {scan_year}年{scan_month}月 共购买成功 {month_purchase_count} 个点播")

            success, message = refresh_token_local(account, config)
            if not success:
                print(f"⚠️ {account_name}: 月份扫描后 Token 刷新失败: {message}")
            else:
                config["accounts"][account_idx] = account
                write_config(config)

            scan_year, scan_month = get_previous_month(scan_year, scan_month)
            if (scan_year < end_year) or (scan_year == end_year and scan_month < end_month):
                print(f"{account_name}: 已达到结束月份 {end_year}年{end_month}月，结束扫描。")
                break

    print("\n====== ONE补充历史0元点播脚本执行完成 ======")
    if total_purchase_count > 0:
        print(f"🎉 本次共成功购买 {total_purchase_count} 个点播")
    else:
        print("ℹ️  本次没有购买到新点播")
    return 0


@capture_output("ONE补充历史0元点播运行结果")
def main():
    try:
        return run_task()
    except KeyboardInterrupt:
        print("\n⚠️  脚本被用户中断")
        return 130
    except Exception as exc:
        print(f"❌ 执行脚本时出现未处理的异常: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
