#多号换行，变量名：sfsyUrl
# const $ = new Env('顺丰速运')
import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta
from sys import exit
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

IS_DEV = False
if os.path.isfile('DEV_ENV.py'):
    import DEV_ENV
    IS_DEV = True

send_msg = ''
one_msg = ''

inviteId = ['FC9A7128E1AE4E419E385FF0DF91B799','D78098B2D29A496CA447D39140C0377F','E5B85228D52845CF94F383F4FEBFA120', 'E5844EF6D2E34B2BB11CFABF13FDB2B4','1F3180464F444406A4DE0B6F4D84E841','C365C74E0B0844FB8C78656FF8375ECD','B9D26F54D0684410B133577D5F9B565D']

class RUN:
    def __init__(self, info, index):
        global one_msg
        one_msg = ''
        split_info = info.split('@')
        url = split_info[0]
        len_split_info = len(split_info)
        last_info = split_info[len_split_info - 1]
        self.send_UID = None
        if len_split_info > 0 and "UID_" in last_info:
            self.send_UID = last_info
        self.index = index + 1
        self.Log(f"\n---------开始执行第{self.index}个账号>>>>>")
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090551) XWEB/6945 Flue',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh',
            'platform': 'MINI_PROGRAM',
        }
        self.deviceId = self.get_deviceId()
        self.login_res = self.login(url)
        self.today = datetime.now().strftime('%Y-%m-%d')

    def get_deviceId(self, characters='abcdef0123456789'):
        return ''.join(random.choice(characters) if c == 'x' else c for c in 'xxxxxxxx-xxxx-xxxx')

    def login(self, sfsyUrl):
        ress = self.s.get(sfsyUrl, headers=self.headers)
        self.user_id = self.s.cookies.get_dict().get('_login_user_id_', '')
        self.phone = self.s.cookies.get_dict().get('_login_mobile_', '')
        self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:]
        if self.phone:
            self.Log(f'用户:【{self.mobile}】登陆成功')
            return True
        else:
            self.Log(f'获取用户信息失败')
            return False

    def getSign(self):
        timestamp = str(int(round(time.time() * 1000)))
        token = 'wwesldfs29aniversaryvdld29'
        sysCode = 'MCS-MIMP-CORE'
        signature = hashlib.md5(f'token={token}&timestamp={timestamp}&sysCode={sysCode}'.encode()).hexdigest()
        self.headers.update({
            'sysCode': sysCode,
            'timestamp': timestamp,
            'signature': signature,
            'deviceId': self.deviceId
        })

    def do_request(self, url, data={}, req_type='post'):
        self.getSign()
        try:
            if req_type == 'post':
                response = self.s.post(url, json=data, headers=self.headers)
            else:
                response = self.s.get(url, headers=self.headers)
                
            if IS_DEV:
                print(f"[DEV] 请求URL: {url}")
                print(f"[DEV] 请求头: {json.dumps(self.headers, indent=2)}")
                print(f"[DEV] 请求参数: {json.dumps(data, indent=2)}")
                print(f"[DEV] 响应数据: {response.text}")
                
            return response.json()
        except Exception as e:
            self.Log(f'请求失败: {str(e)}')
            return None

    def Log(self, msg):
        global one_msg
        one_msg += msg + '\n'
        print(msg)

    # ====================32周年庆任务====================
    def getK32name(self, typeN):
        KName = {
            "CLAIM_CHANCE": "可抽奖次数",
            "DAI_BI": "坐以待币",
            "DING_ZHU": "都顶得住",
            "GAN_FAN": "干饭圣体",
            "ZHI_SHUI": "心如止水",
            "CHENG_GONG": "成功人士",
            "TIETIE_CARD": "贴贴卡",
            "WEALTH_CHANCE": "抽奖机会"
        }
        return KName.get(typeN, f"未知{typeN}")

    def ZNQ32_1(self):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~anniversary2025TaskService~fetchTasksReward'
        response = self.do_request(url, data={
            "channelType": "MINI_PROGRAM",
            "deviceId": self.deviceId
        })
        
        if response:
            if response.get('success'):
                obj = response.get('obj', {})
                currentAccountList = obj.get('currentAccountList', [])
                
                card_details = []
                for card in currentAccountList:
                    card_type = card.get('currency', '')
                    balance = card.get('balance', 0)
                    card_details.append(f"{self.getK32name(card_type)}：{balance}")
                
                if card_details:
                    self.Log("当前卡片详情：" + " | ".join(card_details))
                
                # 开始抽奖
                self.EAR_END_2023_getAward()
            else:
                error_msg = response.get('errorMessage', '未知错误')
                self.Log(f"获取任务奖励失败：{error_msg}")

    def EAR_END_2023_getAward(self):
        self.Log(f'\n>>>>>>开始抽卡')
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~anniversary2025ClaimService~claim'
        for l in range(3):  # 外层循环尝试10次
            for card_type in range(3):  # 卡类型0到2
                json_data = {"cardType": card_type}
                response = self.do_request(url, data=json_data)
                if not response:
                    self.Log(f'卡类型{card_type}抽卡请求失败')
                    continue
                if response.get('success'):
                    received_list = response.get('obj', {}).get('receivedAccountList', [])
                    for card in received_list:
                        currency_name = self.getK32name(card.get('currency'))
                        self.Log(f'卡类型{card_type}抽卡成功 ➜ 获得【{currency_name}】x{card.get("amount", 1)}')
                else:
                    error_msg = response.get('errorMessage', '未知错误')
                    if '余额不足' in error_msg:
                        self.Log(f'卡类型{card_type}余额不足，停止抽卡')
                        break
                    elif '用户信息失效' in error_msg:
                        self.Log('用户信息失效，请重新登录')
                        return
                    else:
                        self.Log(f'卡类型{card_type}抽卡失败：{error_msg}')
                        break
                time.sleep(3)  # 每次抽卡间隔3秒

    def EAR_END_2023_TaskList(self):
        self.Log('\n>>>>>>开始32周年庆任务')
        json_data = {
            "activityCode": "ANNIVERSARY_2025",
            "channelType": "MINI_PROGRAM",
            "deviceId": self.deviceId
        }
        self.headers.update({
            'channel': '32annixcx',
            'syscode': 'MCS-MIMP-CORE'
        })

        # 获取积分信息
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberIntegral~userInfoService~personalInfoNew'
        response = self.do_request(url, data=json_data)
        if response and response.get('success'):
            info = response.get('obj', {})
            self.Log(f'>【{info.get("levelName","未知等级")}】积分 {info.get("availablePoints",0)}')

        # 处理任务列表
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList'
        response = self.do_request(url, data=json_data)
        if response and response.get('success'):
            for task in response.get('obj', []):
                taskName = task.get('taskName', '未知任务')
                taskType = task.get('taskType')
                status = task.get('status')
                
                if status == 3:
                    self.Log(f'>【{taskName}】- 已完成')
                    continue

                # 任务处理逻辑
                if taskType == 'CLICK_MY_SETTING':
                    self.taskCode = task.get('taskCode')
                    self.addDeliverPrefer()
                elif taskType == 'GIVING_BLESS':
                    self.ZNQ32_ZhuFu()
                elif taskType == 'DAILY_SIGN':
                    self.doTask(task.get('taskCode'))

                time.sleep(1)
                self.EAR_END_2023_receiveTask(task.get('taskCode'))

        # 执行后续操作
        self.ZNQ32_1()

    def ZNQ32_ZhuFu(self):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~anniversary2025WishService~sendWish'
        response = self.do_request(url, {
            "deviceId": self.deviceId,
            "wishType": "DEFAULT"
        })
        if response:
            if response.get('success'):
                self.Log("祝福发送成功")
            else:
                self.Log(f"祝福发送失败：{response.get('errorMessage')}")

    def addDeliverPrefer(self):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberIntegral~deliverPreferService~addDeliverPrefer'
        response = self.do_request(url, {
            "deviceId": self.deviceId
        })
        if response and response.get('success'):
            self.Log("地址偏好设置成功")

    def doTask(self, taskCode):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~doTask'
        data = {
            "taskCode": taskCode,
            "deviceId": self.deviceId
        }
        response = self.do_request(url, data)
        if response and response.get('success'):
            self.Log(f"任务【{taskCode}】执行成功")

    def EAR_END_2023_receiveTask(self, taskCode):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~receive'
        data = {
            "taskCode": taskCode,
            "deviceId": self.deviceId
        }
        response = self.do_request(url, data)
        if response and response.get('success'):
            self.Log(f"任务【{taskCode}】领取成功")

    def csy2025(self):
        """
        查询财神爷任务列表，并处理任务逻辑。
        """
        try:
            payload = {"activityCode": "DRAGONBOAT_2025", "channelType": "MINI_PROGRAM"}
            url = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList"

            response = self.do_request(url, payload)

            if isinstance(response, dict) and response.get('success'):
                tasks = response.get('obj', [])
                for task in tasks:
                    taskType = task.get('taskType', None)
                    taskName = task.get('taskName', '未知任务')
                    taskCode = task.get('taskCode', None)
                    taskStatus = task.get('status', 0)

                    self.Log(f"> 正在处理任务【{taskName}】，类型：【{taskType}】，状态：【{taskStatus}】")

                    if taskStatus == 3:
                        self.Log(f"> 任务【{taskName}】已完成，跳过")
                        continue

                    if taskCode:
                        self.DRAGONBOAT_2025_finishTask(taskCode, taskName)
        except Exception as e:
            import traceback
            self.Log(f"任务查询时出现异常：{e}\n{traceback.format_exc()}")

    def lingtili(self):
        try:
            payload = {}
            url = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~dragonBoat2025HastenService~receiveCountdownReward"
            response = self.do_request(url, payload)
            if response and response.get('success'):
                self.Log("领取体力成功")
            else:
                self.Log("领取体力失败")
        except Exception as e:
            import traceback
            self.Log(f"领体力时出现异常：{e}\n{traceback.format_exc()}")

    def cxcs(self):
        self.Log('====== 开始加速 ======')
        try:
            query_payload = {}
            
            query_url = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~dragonBoat2025HastenService~getHastenStatus"
            query_response = self.do_request(query_url, query_payload)

            if query_response.get('success') and query_response.get('obj'):
                wealth_chance = query_response['obj'].get('remainHastenChance', 0)
                
                self.Log(f'当前有 {wealth_chance} 次加速机会')

                if wealth_chance > 0:
                    draw_url = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~dragonBoat2025HastenService~hastenLottery"
                    for i in range(wealth_chance):
                        self.Log(f'>>> 开始第 {i + 1} 次加速')
                        draw_payload = {}
                        draw_response = self.do_request(draw_url, draw_payload)

                        if draw_response.get('success') and draw_response.get('obj'):
                            draw_obj = draw_response.get('obj')
                            received_account_list = draw_obj.get('remainHastenChance', 0)
                            self.Log(f'加速成功: 剩余{received_account_list}次')
                        else:
                            error_message = draw_response.get('errorMessage', '无返回')
                            self.Log(f'加速失败: {error_message}')
                        time.sleep(1)
                else:
                    self.Log('没有剩余的加速机会')

            else:
                error_message = query_response.get('errorMessage', '无法查询加速机会')
                self.Log(f'查询加速机会失败，原因：{error_message}')

        except Exception as e:
            import traceback
            self.Log(f'加速时出现异常：{e}\n{traceback.format_exc()}')

        self.Log('====== 加速结束 ======')

    def index2025(self):
        self.Log(f'====== {self.mobile}开始查询加速状态 ======')

        try:
            query_payload = {}
            query_url = "https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~dragonBoat2025UpgradeService~getUpgradeStatus"
            query_response = self.do_request(query_url, query_payload)

            if query_response.get('success') and query_response.get('obj'):
                obj = query_response.get('obj', {})
                current_account_list = obj.get('levelList', [])

                wealth_counts = {
                    "三轮车": 0,
                    "货车": 0,
                    "冷运车": 0,
                    "轿车": 0,
                    "跑车": 0,
                    "无人机": 0,
                    "高铁": 0,
                    "飞机": 0,
                    "动感飞机": 0,
                    "浪漫飞机": 0,
                    "闪耀飞机": 0,
                    "星际飞机": 0,
                    "时光机": 0,
                }

                for account in current_account_list:
                    currency = account.get('currency')
                    balance = account.get('balance', 0)
                    if currency == "TRICYCLE":
                        wealth_counts["三轮车"] += balance
                    elif currency == "TRUCK":
                        wealth_counts["货车"] += balance
                    elif currency == "COOL_TRUCK":
                        wealth_counts["冷运车"] += balance
                    elif currency == "SEDAN":
                        wealth_counts["轿车"] += balance
                    elif currency == "SPORTS_CAR":
                        wealth_counts["跑车"] += balance
                    elif currency == "DRONE":
                        wealth_counts["无人机"] += balance
                    elif currency == "HSR":
                        wealth_counts["高铁"] += balance
                    elif currency == "PLANE":
                        wealth_counts["飞机"] += balance
                    elif currency == "SEDAN":
                        wealth_counts["动感飞机"] += balance
                    elif currency == "SPORTS_CAR":
                        wealth_counts["浪漫飞机"] += balance
                    elif currency == "DRONE":
                        wealth_counts["闪耀飞机"] += balance
                    elif currency == "HSR":
                        wealth_counts["星际飞机"] += balance
                    elif currency == "PLANE":
                        wealth_counts["时光机"] += balance

                account_log = (
                    f"账号：{self.mobile}\n"
                    f"三轮车有 {wealth_counts['三轮车']} 次抽奖\n"
                    f"货车有 {wealth_counts['货车']} 次抽奖\n"
                    f"冷运车有 {wealth_counts['冷运车']} 次抽奖\n"
                    f"轿车有 {wealth_counts['轿车']} 次抽奖\n"
                    f"跑车有 {wealth_counts['跑车']} 次抽奖\n"
                    f"无人机有 {wealth_counts['无人机']} 次抽奖\n"
                    f"高铁有 {wealth_counts['高铁']} 次抽奖\n"
                    f"飞机有 {wealth_counts['飞机']} 次抽奖\n"
                    f"动感飞机有 {wealth_counts['动感飞机']} 次抽奖\n"
                    f"浪漫飞机有 {wealth_counts['浪漫飞机']} 次抽奖\n"
                    f"闪耀飞机有 {wealth_counts['闪耀飞机']} 次抽奖\n"
                    f"星际飞机有 {wealth_counts['星际飞机']} 次抽奖\n"
                    f"时光机有 {wealth_counts['时光机']} 次抽奖\n"
                )
                self.Log(account_log)

            else:
                error_log = f"账号：{self.mobile} 查询失败或数据为空"
                self.Log(error_log)
        except Exception as e:
            import traceback
            self.Log(f"查询状态时出现异常: {e}\n{traceback.format_exc()}")

    def DRAGONBOAT_2025_finishTask(self, taskCode, taskName):
        try:
            payload = {"taskCode": taskCode}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'

            response = self.do_request(url, payload)

            if isinstance(response, dict) and response.get('success'):
                obj = response.get('obj', None)
                if obj is True:
                    self.Log(f"> {taskName}-已完成")
                    return True
                elif obj is False:
                    self.Log(f"> {taskName}-未完成，失败原因：返回的 obj 为 False，任务可能无效或已完成")
                    return False
                elif isinstance(obj, dict):
                    data = obj.get('data', [])
                    self.Log(f"> {taskName}-已完成，返回数据：{data}")
                    return True
                else:
                    self.Log(f"> {taskName}-未完成，失败原因：返回的 obj 类型未知，实际为: {obj}")
                    return False
            else:
                error_message = response.get('errorMessage', '无返回') if isinstance(response, dict) else '未知错误'
                self.Log(f"> {taskName}-未完成，失败原因：{error_message}")
                return False
        except Exception as e:
            import traceback
            self.Log(f"{taskName}-未完成，任务代码：【{taskCode}】，异常信息：{e}\n{traceback.format_exc()}")
            return False

    def game202505(self):
        self.Log(f'>>>开始连粽子')
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~dragonBoatGame2025Service~win'
        for i in range(1, 5):
            json_data = {
                "levelIndex": i
            }
            response = self.do_request(url, data=json_data)
            if response.get('success') == True:
                self.Log(f'第{i}关成功！')
            else:
                self.Log(f'第{i}关失败！')

    def sendMsg(self):
        global send_msg
        if self.send_UID:
            send_msg += f'{one_msg}'
        else:
            send_msg += f'{one_msg}'

    def main(self):
        global one_msg
        wait_time = random.randint(1000, 3000) / 1000.0
        time.sleep(wait_time)  # 等待
        one_msg = ''
        if not self.login_res: return False
        
        # 添加2025年端午活动相关调用
        self.csy2025()
        self.lingtili()
        self.game202505()  # 添加连粽子游戏
        self.cxcs()
        self.index2025()
        
        # 注释掉已结束的32周年庆活动
        # self.EAR_END_2023_TaskList()
        
        self.sendMsg()
        return True

def start():
    global send_msg, one_msg
    send_msg = ''
    sfsyUrl = os.getenv("sfsyUrl")
    if not sfsyUrl:
        print("未找到环境变量 sfsyUrl")
        exit(1)

    accounts = sfsyUrl.split('\n')
    print(f"共找到{len(accounts)}个账号")
    for index, account in enumerate(accounts):
        run = RUN(account, index)
        if run.main():
            pass
        time.sleep(3)
    if send_msg:
        print(send_msg)

if __name__ == '__main__':
    start()
