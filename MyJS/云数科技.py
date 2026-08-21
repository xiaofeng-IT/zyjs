import requests
import json

# ========== 填写账号密码 ==========
mobile = "你的手机号"
password = "你的密码"
# =================================

def main():
    # 1. 登录
    login_url = "https://api.apiyunhaishengwu.work/api/v1/oauth/login"
    login_payload = {
        "mobile": mobile,
        "password": password
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 14; LE2120 Build/UKQ1.230924.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.119 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/32.0)",
        'Content-Type': "application/json"
    }

    try:
        login_res = requests.post(login_url, data=json.dumps(login_payload), headers=headers, timeout=15)
        login_data = login_res.json()
        print("【登录结果】", login_data)

        if login_data.get("code") == 200:
            token = login_data["access_token"]
            
            # 2. 签到
            sign_url = "https://api.apiyunhaishengwu.work/api/v1/index/signIn"
            sign_payload = {"image": None}
            sign_headers = headers.copy()
            sign_headers["Authorization"] = token

            sign_res = requests.post(sign_url, data=json.dumps(sign_payload), headers=sign_headers, timeout=15)
            print("\n【签到结果】", sign_res.text)
        else:
            print("登录失败")
    except Exception as e:
        print("执行异常：", str(e))

if __name__ == "__main__":
    main()