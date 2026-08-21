"""收益参考:实物/现金
本项目支持双端签到，答题，盲盒抽奖，幸运抽奖，云宠物。
APP抓包
1.手机各大市场下载白鲸旧衣回收这个APP。
2.下载完手机验证码登录便可,登录后点我的-右上角齿轮-点账户安全改密码。
*提交格式:备注#手机号#密码
微信抓包
1.微信搜索白鲸回收,然后微信授权手机登陆。注:登陆后不需要绑定手机如绑定就会同步APP数据,不绑定手机可以撸实物,绑定可以同步APP撸现金需知晓。
2.打开抓包软件抓https://www.52bjy.com/api/app/user.php此域名下的username和auth的2个参数跟APP的CK参数有区别切勿混淆。
*提交格式:备注#username#auth"""

import requests,json,re,os,sys,time,random,datetime,hashlib,base64,urllib3
from urllib.parse import quote
retrycount = 1
environ = "bjhs"
session = requests.session()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#---------------------主代码区块---------------------
def getparm(parm):
    sign = hashlib.md5((parm + Secret).encode('utf-8')).hexdigest()
    return parm + "&sign=" + sign

def run(arg1,arg2,arg3,arg4,arg5):
    global Secret
    header = {
        "Host": "www.52bjy.com",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 8 Build/QKQ1.190828.002; wv) AppleWebKit/537.36",
    }
    if len(arg1) > 11:
        app = 'wx'
        appkey = '1f70a57fdf4061a7'
        Secret = 'eBRaFLkuJ5'
        auth = arg2
    else:
        app = 'self'
        appkey = "a9827e37ed2becd8"
        Secret = 'mCaP57nCwC'
        url = 'https://www.52bjy.com/api/app/member.php?'
        data = f"action=login&username={arg1}&password={arg2}&app={app}&sign="
        response = session.post(url=url, headers=header, data=data).json()
        if "登录成功" not in response.get("message",""):
            print(f"❌ 登录失败：账号或密码错误")
            return
        auth = response["data"]["token"]

    # 用户信息
    userinfo_url = f'https://www.52bjy.com/api/app/user.php?' + getparm(f"action=userinfo&appkey={appkey}&auth={auth}&username={arg1}")
    userinfo = session.get(url=userinfo_url).json()

    # ============== 签到 ==============
    print(f"📌 签到任务")
    urlsign = f'https://www.52bjy.com/api/app/user.php?action=qiandao&app={app}&auth={auth}&username={arg1}'
    res = session.get(url=urlsign, headers=header).json()
    if "签到成功" in res.get("message",""):
        print(f"✅ 签到成功")
    elif "已经签到" in res.get("message",""):
        print(f"✅ 今日已签到")

    # 连签天数
    res_day = session.get(f"https://www.52bjy.com/api/app/user.php?action=getsigninfo&auth={auth}&username={arg1}").json()
    day = res_day['data']["thisturn"]
    print(f"✅ 本周连续签到：{day} 天\n")

    # ============== 答题 ==============
    print(f"📌 答题任务")
    for i in range(7):
        dt = session.get(f'https://www.52bjy.com/api/app/question.php?'+ getparm(f"action=list&appkey={appkey}&username={arg1}&version=1")).json()
        if not dt['isSucess']:
            print(f"✅ 答题已全部完成\n")
            break
        ans = 0
        for idx, val in enumerate(dt['data'][0]['answer']):
            if val['isright'] == "1":
                ans = idx
        tj = session.get(f'https://www.52bjy.com/api/app/question.php?'+ getparm(f"action=addcount&answer={ans}&appkey={appkey}&id={dt['data'][0]['id']}&username={arg1}")).json()
        if tj['isSucess']:
            print(f"✅ 第{dt['data'][0]['index']}题：答对")
            time.sleep(1)
        else:
            print(f"❌ 答题失败")
            break

    # ============== 宠物 ==============
    print(f"\n📌 云宠物任务")
    pet = session.get(f'https://www.52bjy.com/api/app/promotionanimal.php?' + getparm(f"action=adoptanimalshow&appkey={appkey}&username={arg1}")).json()
    if pet['data'].get("exist_pet",0) > 0:
        print(f"✅ 宠物等级：{pet['data']['level']} 级")
        acts = {1:"喂养",2:"喝水",3:"铲屎"}
        for k, v in acts.items():
            res = session.get(f'https://www.52bjy.com/api/app/promotionanimal.php?' + getparm(f"action=adoptinteract&appkey={appkey}&type={k}&username={arg1}")).json()
            if res["isSucess"]:
                print(f"✅ {v}：完成")
            time.sleep(0.5)
    else:
        adopt = session.get(f'https://www.52bjy.com/api/app/promotionanimal.php?' + getparm(f"action=adoptanimal&appkey={appkey}&type=2&username={arg1}")).json()
        if adopt["isSucess"]:
            print(f"✅ 已成功领养宠物")
        else:
            print(f"❌ 未领养宠物")
    print()

    # ============== 抽奖 ==============
    print(f"📌 幸运抽奖")
    for i in range(5):
        res = session.get(url=f'https://www.52bjy.com/api/app/promotionjgg.php?' + getparm(f"action=prize_draw&app={app}&appkey={appkey}&username={arg1}")).json()
        if res["isSucess"]:
            print(f"✅ 抽奖获得：{res['data']['title']}")
            time.sleep(1)
        elif "已用完" in res["message"]:
            print(f"✅ 抽奖次数已用完")
            break
        else:
            break
    print()

    # ============== 资产信息 ==============
    info = session.get(f'https://www.52bjy.com/api/app/user.php?' + getparm(f"action=userinfo&appkey={appkey}&auth={auth}&username={arg1}")).json()
    print(f"📌 账号资产")
    print(f"✅ 鲸鱼币：{info['data']['credit']}")
    print(f"✅ 成长值：{info['data']['growths']}")

def main():
    if os.environ.get(environ):
        ck = os.environ.get(environ)
    else:
        print("❌ 未配置环境变量 bjhs")
        return

    ck_list = [x for x in ck.split('\n') if x.strip()]
    print("="*40)
    print(f"📅 运行时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📌 共加载账号：{len(ck_list)} 个")
    print("="*40+"\n")

    for idx, line in enumerate(ck_list):
        parts = line.strip().split('#')
        if len(parts) != 3:
            print(f"❌ 账号[{idx+1}] 格式错误，跳过\n")
            continue

        mark, acc, paw = parts
        print(f"🚀 开始执行账号：{mark}")
        print("-"*30)
        run(acc, paw, "", "", "")
        print("\n"+"="*40+"\n")
        time.sleep(1)

    print("✅ 所有账号执行完毕！")

if __name__ == '__main__':
    main()