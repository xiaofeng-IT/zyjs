'''
new Env('品赞代理')
注册地址：https://www.ipzan.com?pid=s6r62n2u8
品赞代理每周免费领取金币
变量名：pzdl，格式：备注#手机号码#密码，多个账号新建环境变量或者用&隔开
cron: 0 12 * * *
'''

import os
import sys
import base64
import random
import requests
import traceback



def myexcept(mytype, myvalue, mytraceback):
    for exceptstr in traceback.format_exception(mytype, myvalue, mytraceback):
        print(exceptstr.strip())




sys.excepthook = myexcept

pzdl = os.getenv('pzdl') or ''
pzdlaccounts = pzdl.split('&')
pzdlaccountsnums = len(pzdlaccounts)

for index, pzdlaccountdata in enumerate(pzdlaccounts, 1):
    values = pzdlaccountdata.split('#')
    remark, username, password = values[0], values[1], values[2]
    
    print('========账号%s/%s：%s========' % (index, pzdlaccountsnums, remark))
    

    
    encoded = base64.b64encode(f'{username}QWERIPZAN1290QWER{password}'.encode()).decode()
    randomstr = ''.join(random.choices('0123456789abcdefABCDEF', k=400))
    account = f'{randomstr[:100]}{encoded[:8]}{randomstr[100:200]}{encoded[8:20]}{randomstr[200:300]}{encoded[20:]}{randomstr[300:]}'
    
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    
    resp = requests.post(
        'https://service.ipzan.com/users-login',
        headers=headers,
        json={'account': account, 'source': 'ipzan-home-one'}
    ).json()
    
    message = resp['message']
    
    if message:
        print('登录失败：%s' % message)
    else:
        print('登录成功')
        token = resp['data']['token']
        headers['authorization'] = 'Bearer %s' % token
        
        resp = requests.get(
            'https://service.ipzan.com/home/userWallet-receive',
            headers=headers
        ).json()
        
        message = resp['message']
        
        if message:
            print('每周免费领取金币失败：%s' % message)
        else:
            print('每周免费领取金币成功')
        
        resp = requests.get(
            'https://service.ipzan.com/home/userWallet-find',
            headers=headers
        ).json()
        
        print('余额：%s元' % resp['data']['bonus_amount'])
