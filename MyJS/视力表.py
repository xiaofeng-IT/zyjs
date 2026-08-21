# -*- coding: utf-8 -*-

"""
环境变量:SLB，值手机号#密码#设备号，多账号用 @ 分隔
(设备号为必填项，设备号在我的--右上角“系统”--RegId)
"""

import os
import sys
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("缺少依赖 requests,请在青龙执行: pip install requests")
    sys.exit(1)

BASE = "https://wx.visionsqsm.com/web/api"
VER_NUM = "58"

# 保存每个账号首次生成的随机参数（左右眼视力/年龄等），后续运行复用
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vision_sqsm_settings.json")
_settings_lock = threading.Lock()

# 上报视力测试时使用的固定中文字段值
EYE_LEFT = "左眼"
EYE_RIGHT = "右眼"
TEST_TYPE_SINGLE = "单人"
TEST_TYPE3 = "近视"
# 每日任务名称(与服务端返回一致,用于判断完成情况)
TASK_WATCH = "观看视频"
TASK_VISION = "视力测试"
TASK_SHARE = "分享"

# 多线程打印锁,避免并发日志错行
_print_lock = threading.Lock()


def load_notify():
    """加载青龙自带的通知模块;不存在时退化为控制台打印。"""
    try:
        from notify import send
        return send
    except Exception:
        def _send(title, content):
            print("\n===== %s =====\n%s" % (title, content))
        return _send


notify = load_notify()


def parse_accounts():
    """解析环境变量 SLB 中的账号列表，返回 [(手机号, 密码, 设备号), ...]。
       格式：手机号#密码#设备号，多账号用 @ 隔开。
    """
    raw = os.environ.get("SLB", "").strip()
    if not raw:
        print("未配置环境变量 SLB (格式: 手机号#密码#设备号，多账号用@隔开)")
        sys.exit(1)

    accounts = []
    for item in raw.split("@"):
        item = item.strip()
        if not item:
            continue
        parts = item.split("#")
        if len(parts) < 3:
            print(f"跳过格式错误的账号（需 手机号#密码#设备号）: {item}")
            continue
        phone = parts[0].strip()
        device = parts[-1].strip()
        pwd = "#".join(parts[1:-1]).strip()   # 密码中可能包含 #，故重新组合
        if not phone or not pwd or not device:
            print(f"跳过格式错误的账号（需 手机号#密码#设备号）: {item}")
            continue
        accounts.append((phone, pwd, device))
    return accounts


def load_settings():
    """读取已保存的随机参数（按手机号区分）。"""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(all_settings):
    """将随机参数写回本地文件。"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_settings, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print("保存配置失败: %s" % ex)


def get_account_settings(phone):
    """获取指定手机号的随机参数；首次生成并持久化，后续复用。

    左/右眼视力在 4.5~5.2 之间取值（保留 1 位小数），年龄 12~30。
    """
    with _settings_lock:
        all_settings = load_settings()
        cfg = all_settings.get(phone)
        if not isinstance(cfg, dict) or "left" not in cfg or "right" not in cfg \
                or "age" not in cfg:
            cfg = {
                "left": "%.1f" % random.uniform(4.5, 5.2),
                "right": "%.1f" % random.uniform(4.5, 5.2),
                "age": str(random.randint(12, 30)),
            }
            all_settings[phone] = cfg
            save_settings(all_settings)
        return cfg


def env_int(name, default):
    """读取整型环境变量,失败时返回默认值。"""
    try:
        return max(1, int(os.environ.get(name, str(default)).strip()))
    except Exception:
        return default


class VisionClient:
    """视力表 App 接口客户端,封装登录、每日任务等请求。"""

    def __init__(self, phone, password, device_no):
        self.phone = phone
        self.password = password
        self.device_no = device_no
        self.token = None
        self.user_code = None
        self.s = requests.Session()
        # 固定请求头,模拟安卓客户端
        self.s.headers.update({
            "User-Agent": "okhttp/3.12.0",
            "Accept-Encoding": "gzip",
            "from": "android",
            "verNum": VER_NUM,
            "X-Device-No": self.device_no,
        })

    def _headers(self, json_body=False, empty_post=False):
        """按需构造请求头。"""
        h = {}
        if self.token:
            h["Authorization"] = self.token  # 注意:无 Bearer 前缀
        if json_body:
            h["Content-Type"] = "application/json;charset=UTF-8"
        if empty_post:
            h["Content-Length"] = "0"
        return h

    def _req(self, method, path, params=None, json_body=None, empty_post=False):
        """统一请求封装:网络异常重试一次,token 失效自动重新登录。"""
        url = "%s%s" % (BASE, path)
        data = {}
        for attempt in range(2):
            headers = self._headers(json_body=json_body is not None,
                                    empty_post=empty_post)
            try:
                r = self.s.request(method, url, params=params, json=json_body,
                                   headers=headers, timeout=20)
            except Exception:
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise
            try:
                data = r.json()
            except Exception:
                raise RuntimeError("%s 返回非JSON: %s %s"
                                   % (path, r.status_code, r.text[:120]))
            code = data.get("code")
            if code in (401, 403) and attempt == 0:
                self.login()
                continue
            return data
        return data

    def login(self):
        """手机号+密码登录,获取 JWT。"""
        body = {"imeiMD5": "", "password": self.password,
                "phoneNumber": self.phone, "version": 1}
        r = self.s.post("%s/user/login" % BASE, json=body,
                        headers=self._headers(json_body=True), timeout=20)
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError("登录失败: %s" % data.get("msg"))
        self.token = data["data"]["token"]
        return self.token

    def personal_info(self):
        """获取个人信息,顺带缓存 userCode(分享链接需要)。"""
        data = self._req("GET", "/frame/scFrameUserVip/personalInfo")
        if data.get("code") == 0 and isinstance(data.get("data"), dict):
            self.user_code = data["data"].get("userCode")
        return data

    def points_balance(self):
        """查询积分与可提现余额。"""
        data = self._req("GET", "/frame/userAccount/viewPointsBalance")
        return data.get("data", {}) if data.get("code") == 0 else {}

    def daily_tasks(self):
        """获取每日任务完成情况。"""
        data = self._req("GET", "/yanke/ScPointActivityConfig/dailyTaskCompletion")
        return data.get("data", []) if data.get("code") == 0 else []

    def watch_video_once(self):
        """观看视频一次(空体 POST,每次+1积分)。"""
        return self._req("POST", "/frame/userAccount/watchVideo", empty_post=True)

    def test_config(self):
        """获取默认测试配置。"""
        return self._req("GET", "/yanke/TestConfig/default")

    def submit_vision(self, left, right, age):
        """上报左右眼视力数据(+20积分)。"""
        body = [
            {"testChannel": "android", "testData": str(left), "testEyeType": EYE_LEFT,
             "testOK": "1", "testType": TEST_TYPE_SINGLE, "testType2": "5.0",
             "testType3": TEST_TYPE3, "userAge": str(age)},
            {"testChannel": "android", "testData": str(right), "testEyeType": EYE_RIGHT,
             "testOK": "1", "testType": TEST_TYPE_SINGLE, "testType2": "5.0",
             "testType3": TEST_TYPE3, "userAge": str(age)},
        ]
        return self._req("POST", "/yanke/testData/add", json_body=body)

    def mark_test_vision(self):
        """标记完成视力测试。"""
        return self._req("POST", "/frame/userAccount/testVision", empty_post=True)

    def count_report(self, rtype="voice_test"):
        """上报测试计数记录。"""
        return self._req("POST", "/frame/scFrameUserVip/countReport",
                         json_body={"type": rtype})

    def share_app(self):
        """分享APP(空体 POST,每次+1积分)。"""
        return self._req("POST", "/frame/userAccount/ShareApp", empty_post=True)

    def stat_record(self, rtype):
        """埋点上报(分享后上报 type=4)。"""
        return self._req("POST", "/stat/record", json_body={"type": rtype})


def _task_count(tasks, name):
    """从每日任务列表中提取指定任务的 (已完成次数, 上限, 是否完成)。"""
    for t in tasks:
        if t.get("taskName") == name:
            done = int(t.get("completedCount", 0) or 0)
            limit = int(t.get("limitNum", 0) or 0)
            return done, limit, bool(t.get("completed"))
    return 0, 0, False


def run_account(phone, password, device, opts):
    """执行单个账号的全部每日任务,返回 (账号标识, 日志文本)。"""
    logs = []
    tag = "%s****%s" % (phone[:3], phone[-4:]) if len(phone) >= 7 else phone

    def log(msg):
        line = "[%s] %s" % (tag, msg)
        with _print_lock:
            print(line)
        logs.append(msg)

    try:
        cfg = get_account_settings(phone)
        c = VisionClient(phone, password, device)
        c.login()
        c.personal_info()
        log("登录成功")
        log("使用参数：左眼=%s 右眼=%s 年龄=%s" % (cfg["left"], cfg["right"], cfg["age"]))
    except Exception as ex:
        log("登录失败: %s" % ex)
        return tag, "\n".join(logs)

    # ---- 视力测试(每日上限1次,+20积分)----
    try:
        tasks = c.daily_tasks()
        _, _, vdone = _task_count(tasks, TASK_VISION)
        if vdone:
            log("视力测试:今日已完成,跳过")
        else:
            c.test_config()
            r1 = c.submit_vision(cfg["left"], cfg["right"], cfg["age"])
            log("视力测试上报:%s" % r1.get("msg"))
            r2 = c.mark_test_vision()
            log("测试标记:%s" % r2.get("msg"))
            r3 = c.count_report("voice_test")
            log("记录上报:%s" % r3.get("msg"))
    except Exception as ex:
        log("视力测试异常:%s" % ex)

    # ---- 观看视频(每日上限5次,每次+1积分)----
    try:
        tasks = c.daily_tasks()
        done, limit, _ = _task_count(tasks, TASK_WATCH)
        limit = limit or 5
        target = min(limit, 5)
        need = max(0, target - done)
        log("观看视频:已完成 %d/%d,本次尝试 %d 次" % (done, target, need))
        got = 0
        for _ in range(need):
            r = c.watch_video_once()
            msg = r.get("msg", "")
            if r.get("code") == 0:
                got += 1
                log("  第%d次:%s" % (done + got, msg))
            else:
                log("  观看中止:%s" % msg)
                break
            # 除最后一个外，视频之间随机间隔 60~120 秒
            if got < need:
                wait = random.uniform(60, 120)
                log("  等待 %d 秒后观看下一个视频" % int(wait))
                time.sleep(wait)
        if need == 0:
            log("观看视频:今日已达上限")
    except Exception as ex:
        log("观看视频异常:%s" % ex)

    # ---- 分享(可选,每日上限 20 次,每次+1积分)----
    if opts["share"]:
        try:
            tasks = c.daily_tasks()
            done, limit, sdone = _task_count(tasks, TASK_SHARE)
            limit = limit or 20
            target = min(limit, opts["share_max"])
            need = max(0, target - done)
            log("分享:已完成 %d/%d,本次尝试 %d 次" % (done, target, need))
            got = 0
            for _ in range(need):
                r = c.share_app()
                msg = r.get("msg", "")
                if r.get("code") == 0:
                    got += 1
                    c.stat_record(4)  # 分享后上报埋点
                    log("  第%d次:%s" % (done + got, msg))
                else:
                    log("  分享中止:%s" % msg)
                    break
                if got < need:
                    time.sleep(random.uniform(3, 6))
            if need == 0:
                log("分享:今日已达上限")
        except Exception as ex:
            log("分享异常:%s" % ex)

    # ---- 汇总积分 ----
    try:
        bal = c.points_balance()
        if bal:
            log("当前积分:%s,可提现:%s 元"
                % (bal.get("points"), bal.get("withDrawableAmount")))
    except Exception as ex:
        log("查询积分异常:%s" % ex)

    return tag, "\n".join(logs)


def main():
    accounts = parse_accounts()
    opts = {
        "share": os.environ.get("VISION_SHARE", "1").strip() in ("1", "true", "True", "yes"),
        "share_max": env_int("VISION_SHARE_MAX", 20),
    }
    threads = env_int("VISION_THREADS", 1)
    threads = min(threads, len(accounts))

    print("共 %d 个账号,并发数=%d,分享=%s"
          % (len(accounts), threads, "开启" if opts["share"] else "关闭"))

    results = {}
    if threads <= 1:
        # 单线程按顺序执行
        for idx, (phone, pwd, device) in enumerate(accounts, 1):
            with _print_lock:
                print("\n========== 账号 %d/%d ==========" % (idx, len(accounts)))
            tag, res = run_account(phone, pwd, device, opts)
            results[idx] = (tag, res)
            if idx < len(accounts):
                time.sleep(random.uniform(3, 6))
    else:
        # 多线程并发执行
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = {}
            for idx, (phone, pwd, device) in enumerate(accounts, 1):
                futs[ex.submit(run_account, phone, pwd, device, opts)] = idx
                time.sleep(random.uniform(0.5, 1.5))  # 错开启动,降低风控
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    results[idx] = ("账号%d" % idx, "未捕获异常: %s" % e)

    # 汇总各账号日志,发送通知
    summaries = []
    for idx in sorted(results):
        tag, res = results[idx]
        summaries.append("账号 %d (%s):\n%s" % (idx, tag, res))

    content = "\n\n".join(summaries)
    try:
        notify("视力表-每日任务", content)
    except Exception as ex:
        print("通知发送失败: %s" % ex)


if __name__ == "__main__":
    main()