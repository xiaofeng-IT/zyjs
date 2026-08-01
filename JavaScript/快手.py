#  .............................................
#           __  _
#        .-.'  `; `-._  __  _
#       (_,           .-:'  `; `-._
#     ,'o"(            (_,           )
#    (__,-'            ,'o"(            )
#       (             (__,-'            )
#        `-'._.--._.-'  (             )
#           ||  ||      `-'._.--._.-'
#                      ||  ||
#  .............................................
#               🐑 小羊祈祷 🐑
#           ✨ 代码无错，调试无忧 ✨
#           🐾 变量不丢，函数生效 🐾
#           💾 运行顺利，输出如愿 💾
#           🙏 Bug退散，异常消失 🙏
#           🚀 变量不丢，函数生效 🚀
#           🍀 运行顺利，输出如愿 🍀
#           🧘‍♂️ 心态平和，逻辑清晰 🧘‍♂️
#           🔄 死循环停，依赖不崩 🔄
#           🐍 Python之神庇佑代码 🐍
#  .............................................
#  环境变量 KSQDBX_COOKIE
#  内置ck 多账号&分割
#  格式 备注#cookie#sig3(签到)#sig3(宝箱)
#  .............................................
#  内置变量
CK = ''
#  .............................................
import os
import re
import time
import requests
from urllib.parse import unquote

def get_env():
    global CK
    ck = os.environ.get("KSQDBX_COOKIE") or CK
    if not ck:
        print("未填写CK 退出")
        exit(0)
    ck_list = ck.split("&")
    print(f"共找到{len(ck_list)}个账号")
    return ck_list

def main():
    ck_list = get_env()
    for ck in ck_list:
        if not ck:
            continue
        if "#" in ck:
            remark, ck, sign_sig, box_sig = ck.split("#")
        else:
            remark = ck[:2] + "***" + ck[-3:]
            sign_sig = ""
            box_sig = ""
        print(f"\n======= 开始账号：{remark} =======")
        headers = {
            "User-Agent": "KSQD_ANDROID/3.3.3.3333",
            "Cookie": ck,
        }
        
        # 签到逻辑
        if sign_sig:
            sign_url = f"https://api.kuaishouzt.com/rest/zt/clock/sign?sig3={sign_sig}"
            sign_res = requests.post(sign_url, headers=headers).json()
            if sign_res.get("result") == 1:
                print("签到成功")
            else:
                print(f"签到失败：{sign_res}")
        
        # 宝箱逻辑
        if box_sig:
            box_url = f"https://api.kuaishouzt.com/rest/zt/treasure/box?sig3={box_sig}"
            box_res = requests.post(box_url, headers=headers).json()
            if box_res.get("result") == 1:
                print("宝箱领取成功")
            else:
                print(f"宝箱领取失败：{box_res}")

        time.sleep(3)

if __name__ == "__main__":
    main()