#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONE 白嫖0元点播脚本开始执行
APP下载链接：https://75x8yg27.cyou?code=Mrw1MmaFuU
创建日期：2024-11-18
说明：访问https://onelogin.316199.xyz/ 登录账号（未注册也可直接登录）并获取config.json配置文件，将下载下来的config.json配置文件保存到脚本同级目录
"""

import os
import json
import time
import sys
import base64
import hashlib
import importlib.util
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

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
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.json')

ONE_AES_KEY = b'l*bv%Ziq000Biaog'
ONE_AES_IV = b'8597506002939240'
ONE_SIGN_SECRET = 'm4n2hjPeYWkD6tFpqKF^3HO^h24P@idT'
ONE_IP = '0.0.0.0'
REQUEST_TIMEOUT = 30

# 清理空账号信息
def clean_empty_accounts(config):
    if 'accounts' in config and isinstance(config['accounts'], list):
        # 过滤掉所有必填字段为空的账号
        original_count = len(config['accounts'])
        config['accounts'] = [account for account in config['accounts'] 
                             if account.get('TOKEN') and account.get('USER_KEY')]
        
        # 如果有账号被移除，更新配置文件
        if len(config['accounts']) < original_count:
            print(f"已清理 {original_count - len(config['accounts'])} 个空账号")
            write_config(config)
    
    return config

# 检查配置文件是否存在并验证必要的配置项
def check_config():
    if not os.path.exists(config_path):
        print("=" * 30)
        print("❌ 未找到配置文件config.json")
        print("")
        print("📱 请使用浏览器访问以下网址登录并获取配置文件：")
        print("🔗 https://onelogin.316199.xyz")
        print("")
        print("下载配置文件后，将其放在脚本同级目录下")
        print("=" * 30)
        return False
    
    try:
        config = read_config()
        
        # 清理空账号
        config = clean_empty_accounts(config)
        
        # 检查账号配置
        if not config.get('accounts') or len(config['accounts']) == 0:
            print("配置文件中缺少账号信息，请至少配置一个账号")
            return False
            
        # 确保共用的配置项在根级别存在
        common_fields = ["API_URL", "APP_VERSION", "PLATFORM"]
        missing_common_fields = [field for field in common_fields if not config.get(field)]
        if missing_common_fields:
            print(f"配置文件缺少以下共用配置项: {', '.join(missing_common_fields)}")
            print("请在配置文件中填入这些信息")
            return False
            
        # 检查每个账号的必要字段
        required_account_fields = ["TOKEN", "USER_KEY"]
        for i, account in enumerate(config['accounts']):
            missing_fields = [field for field in required_account_fields if not account.get(field)]
            if missing_fields:
                print(f"账号 {i+1} 缺少以下必要项: {', '.join(missing_fields)}")
                print("请在配置文件中填入这些信息后再运行脚本")
                return False
        
        # 确保SendNotify字段存在
        if 'SendNotify' not in config:
            config['SendNotify'] = False
            write_config(config)
        
        return True
    
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return False

# 读取配置文件
def read_config():
    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

# 写入配置文件
def write_config(config):
    with open(config_path, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

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
    data_bytes = data.encode('utf-8')
    manually_padded = pad(data_bytes, AES.block_size)
    webcrypto_padded = pad(manually_padded, AES.block_size)
    encrypted = AES.new(ONE_AES_KEY, AES.MODE_CBC, ONE_AES_IV).encrypt(webcrypto_padded)
    return base64.b64encode(encrypted).decode('utf-8')

def one_aes_decrypt(encrypted_data):
    encrypted_bytes = base64.b64decode(encrypted_data)
    decrypted = AES.new(ONE_AES_KEY, AES.MODE_CBC, ONE_AES_IV).decrypt(encrypted_bytes)

    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        pass

    decrypted = remove_pkcs7_padding(decrypted)
    return decrypted.decode('utf-8')

def md5_hash(data):
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def parse_uuid_from_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError('无效的JWT格式')

        payload = parts[1].replace('-', '+').replace('_', '/')
        payload += '=' * ((4 - len(payload) % 4) % 4)
        decoded_payload = json.loads(base64.b64decode(payload).decode('utf-8'))

        uuid = decoded_payload.get('uuid')
        if not uuid:
            raise ValueError('Token中未找到UUID字段')

        return uuid
    except Exception as e:
        raise ValueError(f'Token解析失败: {e}')

def generate_one_sign(ip, timestamp, user_key, uuid, platform):
    sign_str = f'{ip}.{platform}.{timestamp}.{user_key}.{uuid}'
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
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'UUID': uuid,
        'User-Key': user_key,
        'Accept': 'application/json text/plain */*',
        'App-Version': app_version,
        'Timestamp': timestamp,
        'App_Version': app_version,
        'Accept-Language': 'zh-CNzh-Hans;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Platform': platform,
        'Token': token,
        'IP': ONE_IP,
        'User-Agent': 'Decryptchatr/2 CFNetwork/3826.400.120 Darwin/24.3.0',
        'Sign': sign,
        'Cookie': 'X-SUDUN-WAF-R-C=0001690393',
    }

def build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform):
    return {
        'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
        'uuid': uuid,
        'user-key': user_key,
        'accept': 'application/json, text/plain, */*',
        'app-version': app_version,
        'timestamp': timestamp,
        'app_version': app_version,
        'accept-language': 'zh-CN,zh-Hans;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'platform': platform,
        'token': token,
        'ip': ONE_IP,
        'user-agent': 'PullUpTag/1 CFNetwork/1474 Darwin/23.0.0',
        'cookie': 'X-SUDUN-WAF-R-C=0001690476',
        'sign': sign,
    }

def build_one_context(account, config):
    token = account['TOKEN']
    user_key = account['USER_KEY']
    platform = str(config.get('PLATFORM', '2'))
    uuid = parse_uuid_from_token(token)
    timestamp = str(int(time.time()))
    sign = generate_one_sign(ONE_IP, timestamp, user_key, uuid, platform)
    return token, user_key, uuid, timestamp, sign, platform

# 本地刷新Token
def refresh_token_local(account, config):
    try:
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config['APP_VERSION'])

        payload = (
            f'channel_code=&timestamp={timestamp}&token={token}&uuid={uuid}'
            f'&app-version={app_version}&app_version={app_version}&user-key={user_key}'
            f'&platform={platform}&ip={ONE_IP}&sign={sign}'
        )
        headers = build_refresh_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(config['API_URL'], payload, headers)

        if data.get('code') == 200:
            user_data = data['data']['user']
            new_token = user_data.get('token')
            if not new_token:
                return False, "Token为空，请重新获取账号配置"
            account['TOKEN'] = new_token
            account['nickname'] = user_data.get('nickname', account.get('nickname', ''))
            account['avatar'] = user_data.get('avatar', account.get('avatar', ''))
            account['integral'] = user_data.get('integral', account.get('integral', 0))
            account['login_ip'] = user_data.get('login_ip', account.get('login_ip', ''))
            account['updated_at'] = user_data.get('updated_at', account.get('updated_at', ''))

            if 'domain' in data.get('data', {}) and 'api' in data['data']['domain']:
                api_list = data['data']['domain']['api']
                config['api_list'] = api_list

                current_buy_url = config.get('buy_url', '')
                if current_buy_url not in api_list and api_list:
                    config['buy_url'] = api_list[0]

            return True, "Token更新成功"
        return False, f"请求失败: {data.get('mezsage', data.get('message', '未知错误'))}"
    except Exception as e:
        return False, f"刷新Token失败: {e}"

# 本地获取文章列表
def get_article_list_local(account, config, published_at, page=1):
    try:
        buy_url = config.get('buy_url', config['api_list'][0] if config.get('api_list') else 'https://api.pjq6he.com')
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config['APP_VERSION'])
        page_size = 20

        payload = (
            f'published_at={published_at}&model_id=6&page={page}&size={page_size}'
            f'&sort=published_at&buy_type=0&timestamp={timestamp}&token={token}&uuid={uuid}'
            f'&app-version={app_version}&app_version={app_version}&user-key={user_key}'
            f'&platform={platform}&ip={ONE_IP}&sign={sign}'
        )
        headers = build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(f"{buy_url.rstrip('/')}/v2.5/article/discovery", payload, headers)
        return True, data
    except Exception as e:
        return False, str(e)

# 本地执行购买操作
def purchase_item_local(account, config, item_id):
    try:
        buy_url = config.get('buy_url', config['api_list'][0] if config.get('api_list') else 'https://api.pjq6he.com')
        token, user_key, uuid, timestamp, sign, platform = build_one_context(account, config)
        app_version = str(config['APP_VERSION'])

        payload = (
            f'id={item_id}&timestamp={timestamp}&token={token}&uuid={uuid}'
            f'&app-version={app_version}&app_version={app_version}&user-key={user_key}'
            f'&platform={platform}&ip={ONE_IP}&sign={sign}'
        )
        headers = build_buy_headers(token, user_key, uuid, timestamp, sign, app_version, platform)
        data = request_one_api(f"{buy_url.rstrip('/')}/v2.5/purchase/buy", payload, headers)
        return True, data
    except Exception as e:
        return False, str(e)

# 执行购买操作的函数
def execute_freebuy():
    # 读取配置
    config = read_config()
    
    # 清理空账号
    config = clean_empty_accounts(config)
    
    # 获取公共配置
    accounts = config['accounts']
    
    # 统计购买成功的数量
    purchase_count = 0
    
    for account_idx, account in enumerate(accounts):
        account_name = account.get('nickname', f'账号{account_idx+1}')
        print(f"\n正在为 {account_name} 执行白嫖购买操作...")
        
        try:
            # 刷新Token
            success, mezsage = refresh_token_local(account, config)
            if success:
                print(f"{account_name} Token刷新成功")
                # 更新配置
                config['accounts'][account_idx] = account
                write_config(config)
            else:
                print(f"❌ {account_name} Token刷新失败: {mezsage}")
                continue
            
            # 获取当前月份
            current_year, current_month = datetime.now().year, datetime.now().month
            published_at = f"20;{current_year - 2020}-{current_month}"
            
            # 获取文章列表
            success, data = get_article_list_local(account, config, published_at, 1)
            
            if not success:
                print(f"❌ {account_name} 获取文章列表失败: {data}")
                continue
            
            # 查找buy和coin同时为0的数据
            if not data.get('data'):
                print(f"{account_name} 没有找到可以购买的点播")
                continue
            
            buyable_items = [item for item in data['data'] if item['buy'] == 0 and item['coin'] == '0']
            
            if not buyable_items:
                print(f"{account_name} 本次没有找到可以购买的点播")
            else:
                for item in buyable_items:
                    buy_id = item['id']
                    buy_title = item['title']
                    print(f"尝试为账号 {account_name} 购买ID为 {buy_id} 的点播，标题为 {buy_title}")
                    
                    # 执行购买
                    success, buy_data = purchase_item_local(account, config, buy_id)
                    
                    if success:
                        result = buy_data.get('mezsage', '未知')
                        print(f"✅ {account_name} 购买成功: {buy_title} - {result}")
                        purchase_count += 1
                    else:
                        print(f"❌ {account_name} 购买失败: {buy_title} - {buy_data}")
        
        except Exception as e:
            print(f"❌ 处理账号 {account_name} 时发生错误: {e}")
    
    return purchase_count

# 主函数
def main():
    # 检查配置文件
    if not check_config():
        return
    
    print("\n====== ONE白嫖脚本开始执行 ======")
    print("脚本作者:3iXi,版本:V10,更新时间:26/05/22")
    print("https://github.com/3ixi")
    print("本脚本免费使用,让你付费的均是骗子")
    
    enable_notify = False
    
    try:
        # 读取配置文件
        config = read_config()
        
        # 获取账号数量
        accounts = config.get('accounts', [])
        account_count = len(accounts)
        
        if account_count == 0:
            print("配置文件中没有账号信息，请先配置账号")
            return
        
        print(f"共有 {account_count} 个账号配置")
        
        # 判断是否需要启用SendNotify
        enable_notify = config.get('SendNotify', False)
        if enable_notify:
            try:
                from SendNotify import start_capture, stop_capture_and_notify
                start_capture()
                print("✅ SendNotify通知已启用\n")
            except ImportError:
                print("⚠️ 未找到SendNotify.py模块，将不发送通知\n")
                enable_notify = False
        
        # 执行购买流程
        purchase_count = execute_freebuy()
        
        print("\n====== ONE白嫖脚本执行完成 ======")
        
        if purchase_count > 0:
            print(f"🎉 本次共成功购买 {purchase_count} 个点播")
            # 只有购买成功时才发送通知
            if enable_notify:
                from SendNotify import stop_capture_and_notify
                stop_capture_and_notify("ONE白嫖脚本执行结果")
        else:
            print("ℹ️  本次没有购买到新点播")
            # 没有购买到点播时停止捕获但不发送通知
            if enable_notify:
                from SendNotify import _global_output_capture
                _global_output_capture.stop_capture()
            
    except KeyboardInterrupt:
        print("\n⚠️  脚本被用户中断")
        # 中断时如果有购买成功才发送通知
        if enable_notify:
            try:
                if 'purchase_count' in locals() and purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE白嫖脚本执行结果")
                else:
                    from SendNotify import _global_output_capture
                    _global_output_capture.stop_capture()
            except:
                pass
    except Exception as e:
        print(f"❌ 执行脚本时出现未处理的异常: {e}")
        # 异常时如果有购买成功才发送通知
        if enable_notify:
            try:
                if 'purchase_count' in locals() and purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE白嫖脚本执行结果")
                else:
                    from SendNotify import _global_output_capture
                    _global_output_capture.stop_capture()
            except:
                pass

if __name__ == "__main__":
    main()
