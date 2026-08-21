#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
import json

# 固定域名（如果域名变更，请手动修改）
BASE_URL = "https://wapf8r.wjshf7e7h.cc"

def main():
    # 1. 读取环境变量
    env = os.environ.get('GMGK_QD')
    if not env:
        print("❌ 未找到环境变量 GMGK_QD，请设置手机号#密码")
        sys.exit(1)

    try:
        phone, password = env.split('#', 1)
    except ValueError:
        print("❌ 环境变量格式错误，应为 手机号#密码")
        sys.exit(1)

    # 2. 创建会话（自动管理 cookie）
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 16; 23113RKC6C Build/BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36 YbT36Ksshe72k LT-APP/48/100/YM-RT/',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': BASE_URL,
        'Referer': f'{BASE_URL}/login/login.shtml',
    })

    # 3. 登录
    login_url = f'{BASE_URL}/login/login.shtml'
    login_data = {
        'username': phone,
        'password': password
    }

    try:
        resp = session.post(login_url, data=login_data, timeout=15)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        sys.exit(1)

    if result.get('code') != 200:
        print(f"❌ 登录失败: {result.get('msg', '未知错误')}")
        sys.exit(1)

    print(f"✅ 登录成功，用户: {phone}")

    # 4. 签到
    sign_url = f'{BASE_URL}/mobile/sign/sign'
    # 签到需要携带 token，但 session 已自动保存登录返回的 cookie
    # 额外设置 Referer
    session.headers.update({
        'Referer': f'{BASE_URL}/index/index.shtml',
        'Content-Length': '0',   # 可选，requests 自动计算
    })

    try:
        resp = session.post(sign_url, data={}, timeout=15)  # 空 body
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        print(f"❌ 签到请求失败: {e}")
        sys.exit(1)

    # 签到返回的 code 是布尔值 true，判断方式
    if result.get('code') is True:
        print(f"✅ 签到成功: {result.get('msg', '')} (积分: {result.get('num', '')})")
    else:
        print(f"❌ 签到失败: {result.get('msg', '未知错误')}")
        sys.exit(1)

if __name__ == '__main__':
    main()