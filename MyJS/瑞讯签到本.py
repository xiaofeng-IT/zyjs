#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
============================================
瑞讯签到脚本
环境变量：RX
格式：手机号#密码
多账号用 @ 分隔
============================================
"""

import os
import sys
import requests

# API 基础地址（如需正式环境请修改）
BASE_URL = 'https://test-r2wa-api.rwaainet.com'

# 登录接口（用户名密码登录）
SIGN_IN_URL = f'{BASE_URL}/api/auth/sign-in/username'

# 签到接口
CHECKIN_URL = f'{BASE_URL}/api/checkIns'

# 公共请求头
COMMON_HEADERS = {
    'rwa-app-platform': 'expo',
    'expo-origin': 'r2wa://',
    'x-skip-oauth-proxy': 'true',
    'origin': 'https://r2wa.rwaainet.com',
    'Content-Type': 'application/json',
    'User-Agent': 'okhttp/4.12.0',
    'Host': 'test-r2wa-api.rwaainet.com',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip'
}

def login(phone, password):
    """使用用户名（手机号）和密码登录，获取 token"""
    payload = {
        'username': phone,
        'password': password
    }
    try:
        resp = requests.post(SIGN_IN_URL, json=payload, headers=COMMON_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('token')
            if token:
                return token
            else:
                print(f'[错误] 账号 {phone} 登录成功但未返回 token: {data}')
        else:
            print(f'[错误] 账号 {phone} 登录失败，状态码 {resp.status_code}: {resp.text}')
    except Exception as e:
        print(f'[异常] 账号 {phone} 登录请求发生异常: {e}')
    return None

def check_in(token, phone):
    """执行签到"""
    headers = COMMON_HEADERS.copy()
    headers['authorization'] = f'Bearer {token}'
    payload = {'checkInType': 'app'}
    try:
        resp = requests.post(CHECKIN_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            check_in_at = data.get('checkInAt', '未知时间')
            print(f'[成功] 账号 {phone} 签到成功，签到时间: {check_in_at}')
        else:
            print(f'[失败] 账号 {phone} 签到失败，状态码 {resp.status_code}: {resp.text}')
    except Exception as e:
        print(f'[异常] 账号 {phone} 签到请求发生异常: {e}')

def main():
    # 从环境变量 RX 获取账号信息
    rx = os.getenv('RX')
    if not rx:
        print('错误：未设置环境变量 RX，请按 "手机号#密码" 或 "手机号#密码@手机号#密码" 格式设置')
        sys.exit(1)

    accounts = rx.split('@')
    if not accounts:
        print('错误：环境变量 RX 为空')
        sys.exit(1)

    for account in accounts:
        if '#' not in account:
            print(f'警告：账号 "{account}" 格式不正确，跳过')
            continue
        phone, password = account.split('#', 1)
        phone = phone.strip()
        password = password.strip()
        if not phone or not password:
            print(f'警告：账号 "{account}" 手机号或密码为空，跳过')
            continue

        print(f'--- 开始处理账号 {phone} ---')
        token = login(phone, password)
        if token:
            check_in(token, phone)
        else:
            print(f'[失败] 账号 {phone} 获取 token 失败，跳过签到')
        print('--- 处理结束 ---\n')

if __name__ == '__main__':
    main()