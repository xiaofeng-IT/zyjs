#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Update : 2025/10/10
# @env : iqyck
# 功能：匹配指定会员有效期显示格式
# -------------------------------
"""
环境变量：
1. export iqiyi_v7_last_get = "2025-10-05"  # 上次领取日期（YYYY-MM-DD）
2. export iqyck = "你的爱奇艺Cookie"
"""
from time import sleep, time
from datetime import datetime, timedelta
from os import environ, system, path
from re import findall
from sys import exit, stdout
from uuid import uuid4
import requests

def load_send():
    cur_path = path.abspath(path.dirname(__file__))
    if path.exists(cur_path + "/notify.py"):
        try:
            from notify import send
            return send
        except ImportError:
            return False
    return False

try:
    from requests import Session
    from fake_useragent import UserAgent
except:
    print("安装依赖库...")
    system("pip3 install fake-useragent requests")
    print("安装完成，重新运行脚本")
    exit(0)

# 读取环境变量
iqyck = environ.get("iqyck") or ""
last_get_date_str = environ.get("iqiyi_v7_last_get") or ""
P00001 = P00003 = dfp = qyid = ""
if not iqyck:
    print("❌ 缺少iqyck环境变量")
    exit(0)

# 提取Cookie参数
for item in ["P00001", "P00003", "QC005", "__dfp"]:
    for iqy in iqyck.split("&&"):
        match = findall(rf"{item}=(.*?)(;|$)", iqy)
        if match:
            val = match[0][0]
            if item == "P00001":
                P00001 = val
            elif item == "P00003":
                P00003 = val
            elif item == "QC005":
                qyid = val
            elif item == "__dfp":
                dfp = val.split("@")[0]

class IQiYi:
    def __init__(self):
        self.P00001 = P00001
        self.userId = P00003
        self.dfp = dfp
        self.qyid = qyid
        self.session = Session()
        self.user_agent = UserAgent().chrome
        self.cookie_valid = True
        self.today = datetime.now()
        self.last_get_date = None
        self.user_info = ""  # 初始化用户信息
        self.task_info = ""  # 初始化任务信息
        if last_get_date_str:
            try:
                self.last_get_date = datetime.strptime(last_get_date_str, "%Y-%m-%d")
            except:
                print(f"⚠️ 上次领取日期格式错误：{last_get_date_str}")

    def print_now(self, content):
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {content}")
        stdout.flush()

    def get_userinfo(self):
        self.print_now("🔍 查询用户信息...")
        vip_url = "https://vinfo.vip.iqiyi.com/external/vip_users"
        params = {
            "platform": "bb35a104d95490f6",
            "bizSource": "vip_h5",
            "version": "7.0",
            "vipTypes": "1,4,16,58,56",
            "messageId": "55b1973af62a4868c41ec48a71803d40",
            "_": int(time() * 1000)
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 IqiyiApp/iqiyi IqiyiVersion/16.9.5  IqiyiPlatform/2_22_221 WebVersion/QYWebContainer QYStyleModel/(dark)",
            "Cookie": f"P00001={self.P00001}",
            "Origin": "https://cashier.iqiyi.com",
            "Referer": "https://cashier.iqiyi.com/",
        }
        try:
            # 基础信息请求
            base_url = "https://tc.vip.iqiyi.com/growthAgency/v2/growth-aggregation"
            base_params = {
                "messageId": "b7d48dbba64c4fd0f9f257dc89de8e25",
                "platform": "97ae2982356f69d8",
                "P00001": self.P00001,
                "responseNodes": "duration,growth,upgrade,viewTime,growthAnnualCard",
                "_": int(time() * 1000)
            }
            base_resp = requests.get(base_url, params=base_params, headers={"User-Agent": self.user_agent, "Cookie": f"P00001={self.P00001}"})
            base_data = base_resp.json()

            if base_resp.status_code != 200 or base_data.get("code") != "A00000":
                self.cookie_valid = False
                self.user_info = "⚠️ Cookie失效，请更新\n"
                return

            # 会员信息请求
            vip_resp = requests.get(vip_url, params=params, headers=headers)
            vip_data = vip_resp.json()

            if base_data.get("code") == "A00000":
                user_data = base_data["data"]["user"]
                growth = base_data["data"]["growth"]
                self.user_info += f"✨ 用户昵称：{user_data.get('nickname', '未知')}\n"
                self.user_info += f"🎖️ VIP等级：{growth.get('level', '未知')}\n"
                self.user_info += f"📈 当前成长：{growth.get('growthvalue', '未知')}\n"

            if vip_data.get("code") == "A00000" and "vip_info" in vip_data["data"]:
                vip = vip_data["data"]["vip_info"]
                
                # 星钻会员有效期
                star_diamond_deadline = vip.get("deadline", {}).get("date", "未知")
                if "年" in star_diamond_deadline:
                    star_diamond_deadline = star_diamond_deadline.replace("年", "-").replace("月", "-").replace("日", "")
                self.user_info += f"🎟️ 星钻VIP会员有效期: {star_diamond_deadline}\n"
                
                # 黄金会员有效期
                gold_deadline = vip.get("longestDeadline", {}).get("date", "未知")
                if "年" in gold_deadline:
                    gold_deadline = gold_deadline.replace("年", "-").replace("月", "-").replace("日", "")
                self.user_info += f"🎟️ 黄金VIP会员有效期: {gold_deadline}\n"

                # 剩余天数校验
                if "deadline" in vip and "t" in vip["deadline"]:
                    try:
                        deadline_ts = vip["deadline"]["t"] / 1000
                        deadline_date = datetime.fromtimestamp(deadline_ts)
                        days_left = (deadline_date - self.today).days
                        if days_left < 30:
                            self.user_info += f"⚠️ 剩余{days_left}天，不足30天\n"
                    except:
                        pass
            else:
                self.user_info += "❌ 会员信息获取失败\n"
        except Exception as e:
            self.cookie_valid = False
            self.user_info = f"⚠️ 查询异常：{str(e)}\n⚠️ Cookie可能失效\n"

    def get_next_date(self):
        if self.last_get_date:
            return self.last_get_date + timedelta(days=30)
        return self.today + timedelta(days=30)

    def v7_benefit(self):
        if not self.cookie_valid:
            self.task_info += "⚠️ Cookie失效，跳过领取\n"
            return

        self.print_now("🚀 执行权益领取...")
        url = "https://act.vip.iqiyi.com/level-right/receive"
        headers = {
            "Host": "act.vip.iqiyi.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://vip.iqiyi.com",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
            "Referer": "https://vip.iqiyi.com/",
        }
        data = {
            "code": "k8sj74234c683f",
            "P00001": self.P00001,
            "dfp": self.dfp,
            "qyid": self.qyid,
            "platform": "97ae2982356f69d8",
            "ptid": "02030031010000000000",
        }

        try:
            resp = requests.post(url, headers=headers, data=data)
            self.print_now(f"📡 状态码：{resp.status_code}")
            resp_data = resp.json()

            if resp_data.get("code") == "A00000":
                self.print_now("🎉 领取成功！")
                self.task_info += "🎉 权益领取成功\n"
                next_date = self.get_next_date().strftime("%Y-%m-%d")
                self.task_info += f"下次可领：{next_date}\n"
                self.task_info += "提示：更新iqiyi_v7_last_get为当前日期\n"
            else:
                msg = resp_data.get("msg", "未知错误")
                if "超过领取次数" in msg or "本月已领取" in msg:
                    display_msg = "您本月已领取此权益，下月再来吧！"
                else:
                    display_msg = msg
                self.print_now(f"❌ 领取失败：{display_msg}")
                self.task_info += f"❌ 领取失败：{display_msg}\n"
                if "超过领取次数" in msg or "本月已领取" in msg:
                    next_date = self.get_next_date().strftime("%Y-%m-%d")
                    self.task_info += f"下次可领：{next_date}\n"
        except Exception as e:
            self.print_now(f"⚠️ 任务异常：{str(e)}")
            self.task_info += f"⚠️ 任务异常：{str(e)}\n"
        sleep(3)

    def main(self):
        start = time()
        self.print_now("===== 🎬 任务启动 =====")
        if self.last_get_date:
            self.print_now(f"📅 上次领取：{self.last_get_date:%Y-%m-%d}")
        
        self.get_userinfo()
        self.v7_benefit()

        self.msg = self.user_info + "\n" + self.task_info
        send = load_send()
        if send:
            send("爱奇艺V7权益", self.msg)
            self.print_now("📨 通知已发")
        else:
            self.print_now("❌ 通知服务未加载")

        end = time()
        self.print_now(f"===== 🎬 任务结束 =====")
        self.print_now(f"⏱️ 耗时：{round(end - start, 2)} 秒")
        self.print_now(f"🕒 当前时间：{datetime.now():%Y-%m-%d %H:%M:%S}")

if __name__ == '__main__':
    iqiyi = IQiYi()
    iqiyi.main()