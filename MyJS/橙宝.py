#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 账号配置（文件最前端）
ACCOUNT_LIST = [
    "账号01#用户id#115.29.185.43:443"
]

import time
import random
import json
import uuid
import requests
import urllib3
import threading
import signal
urllib3.disable_warnings()

# Ctrl+C全局退出捕获
EXIT_FLAG = False
def exit_handler(sig, frame):
    global EXIT_FLAG
    print("\n检测到Ctrl+C，停止所有线程并退出")
    EXIT_FLAG = True
signal.signal(signal.SIGINT, exit_handler)

# 抓包固定常量，无额外自定义内容
HOST = "app.chengbaojiayuan.cn"
URL_PATH = "/app?r=guanggao/addAdLog"
PKG_NAME = "com.chengbaojiayuan.app"
AD_TYPE = "信息流广告"
PLATFORM = "gromore"
SDK_NAME = "pangle"
DEV_BRAND = "Redmi"#手机品牌34-37都是设备信息
DEV_TYPE = "M2012K11AC"
DEV_CODE = "alioth"
OS_VER = "13"
FINGER_TPL = "Redmi/alioth/alioth:13/TKQ1.221114.001/V816.0.10.0.TKHCNXM:user/release-keys"
MAC_ENC = "02%3A00%3A00%3A00%3A00%3A00"

# 业务数值区间，未改动ECPM原始范围
ECPM_MIN = 8000
ECPM_MAX = 15000
SLEEP_MIN = 30
SLEEP_MAX = 70
SLEEP_FLOAT = 20
START_DELAY_MAX = 35
COIN_LIMIT = 1000000000
LONG_SLEEP_MIN = 120
LONG_SLEEP_MAX = 180
LONG_SLEEP_FLOAT = 25

# 金币停滞记录
stagnant_count = 0
last_hongbao = None

# 生成抓包匹配随机可变字段
def gen_random_fields():
    android_id = "".join(random.choices("0123456789abcdef", k=16))
    dev_id = f"TKQ1.221114.00{random.randint(1,9)}"
    host_id = random.randint(300000, 340000)
    dev_host = f"pangu-build-component-system-{host_id}-l6pw5-c1hdk-f4zbp"
    req_uuid = f"{uuid.uuid4()}{random.randint(1000,9999)}"
    slot_id = random.randint(982600000, 982699999)
    prime_rit = random.randint(104100000, 104199999)
    ecpm_val = round(random.uniform(ECPM_MIN, ECPM_MAX), 3)
    return {
        "androidId": android_id,
        "device_id": dev_id,
        "device_host": dev_host,
        "requestId": req_uuid,
        "slotId": slot_id,
        "prime_rit": prime_rit,
        "ecpm": ecpm_val
    }

# 构建标准form表单，仅信息流广告，无自检逻辑
def build_form(userid: str):
    rand_data = gen_random_fields()
    fingerprint_enc = FINGER_TPL.replace("/","%2F").replace(":","%3A")
    form = (
        f"userid={userid}"
        f"&device_platform=android"
        f"&device_type={DEV_TYPE}"
        f"&device_brand={DEV_BRAND}"
        f"&device_device={DEV_CODE}"
        f"&device_serial=unknown"
        f"&device_fingerprint={fingerprint_enc}"
        f"&device_host={rand_data['device_host']}"
        f"&device_id={rand_data['device_id']}"
        f"&packageName={PKG_NAME}"
        f"&latitude=0.0&longitude=0.0"
        f"&androidId={rand_data['androidId']}"
        f"&macAddress={MAC_ENC}"
        f"&ismoniqi=0&isroot=0&isusb=0&iskaifazhe=0&isdaili=0"
        f"&os_version={OS_VER}"
        f"&requestId={rand_data['requestId']}"
        f"&slotId={rand_data['slotId']}"
        f"&prime_rit={rand_data['prime_rit']}"
        f"&ecpm={rand_data['ecpm']}"
        f"&adType={AD_TYPE}"
        f"&platform={PLATFORM}"
        f"&sdkName={SDK_NAME}"
    )
    return form, rand_data["ecpm"]

# 发送POST请求，删除表单打印，仅输出返回数据
def send_request(userid: str):
    headers = {
        "Accept-Language": "zh-CN,zh;q=0.8",
        "User-Agent": "okhttp-okgo/jeasonlzy",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Host": HOST
    }
    form_data, ecpm = build_form(userid)
    full_url = f"http://{HOST}{URL_PATH}"
    # 移除打印【本次提交表单】代码段
    try:
        resp = requests.post(full_url, data=form_data, headers=headers, timeout=15, verify=False)
        resp_json = resp.json()
        print("【服务端返回】")
        print(json.dumps(resp_json, ensure_ascii=False))
        return resp_json, ecpm
    except Exception as err:
        print(f"请求异常：{str(err)}")
        return None, ecpm

# 单轮上报循环
def single_task(acc_info):
    global EXIT_FLAG, stagnant_count, last_hongbao
    if EXIT_FLAG:
        return 0
    now = time.strftime("%H:%M:%S")
    note = acc_info["note"]
    uid = acc_info["userid"]
    resp, ecpm = send_request(uid)
    curr_hb = "未获取"
    if resp and resp.get("code") == 200 and isinstance(resp.get("data"), dict):
        curr_hb = resp["data"]["hongbao"]
    # 金币停滞判断
    if isinstance(curr_hb, int):
        if last_hongbao == curr_hb:
            stagnant_count += 1
        else:
            stagnant_count = 0
            last_hongbao = curr_hb
    # 随机冷却休眠
    if random.random() < 0.25:
        cool_sec = random.randint(10, 25)
        print(f"[{now}] 随机冷却{cool_sec}s")
        remain = cool_sec
        step = 0.5
        while remain > 0 and not EXIT_FLAG:
            time.sleep(min(step, remain))
            remain -= step
    # 计算等待时长
    if isinstance(curr_hb, int) and curr_hb >= COIN_LIMIT:
        wait = random.uniform(LONG_SLEEP_MIN, LONG_SLEEP_MAX) + random.uniform(-LONG_SLEEP_FLOAT, LONG_SLEEP_FLOAT)
        wait = max(5, wait)
        print(f"[{now}] {note}金币达上限，长延时{wait:.1f}s")
    else:
        base_wait = random.uniform(SLEEP_MIN, SLEEP_MAX)
        extra_wait = stagnant_count * 10 if stagnant_count >= 2 else 0
        wait = base_wait + random.uniform(-SLEEP_FLOAT, SLEEP_FLOAT) + extra_wait
        wait = max(5, wait)
        if stagnant_count >= 2:
            print(f"[{now}] {note}连续{stagnant_count}轮金币无增长，延长等待")
    print(f"[{now}] eCPM:{ecpm:.3f} | 当前红包:{curr_hb} | 下轮等待{wait:.1f}s\n")
    return wait

# 账号独立线程循环
def account_loop(note, userid):
    global EXIT_FLAG
    delay = random.uniform(0, START_DELAY_MAX)
    if delay > 0:
        print(f"[{time.strftime('%H:%M:%S')}] 【{note}】启动延迟{delay:.1f}s")
        time.sleep(delay)
    print(f"[{time.strftime('%H:%M:%S')}] 账号【{note}】线程启动")
    info = {"note": note, "userid": userid}
    while not EXIT_FLAG:
        wait_time = single_task(info)
        remain = wait_time
        step = 0.5
        while remain > 0 and not EXIT_FLAG:
            time.sleep(min(step, remain))
            remain -= step
    print(f"[{time.strftime('%H:%M:%S')}] 账号【{note}】线程退出")

# 程序入口
def main():
    print(f"[{time.strftime('%H:%M:%S')}] 信息流广告上报脚本启动，Ctrl+C退出\n")
    thread_list = []
    for line in ACCOUNT_LIST:
        line = line.strip()
        if not line:
            continue
        parts = line.split("#")
        if len(parts) != 3:
            print(f"账号配置格式错误：{line}")
            continue
        acc_note = parts[0]
        acc_uid = parts[1].strip()
        t = threading.Thread(target=account_loop, args=(acc_note, acc_uid), daemon=False)
        thread_list.append(t)
        t.start()
    if not thread_list:
        print("无有效账号，程序退出")
        return
    print(f"成功启动{len(thread_list)}个账号线程\n")
    try:
        for t in thread_list:
            t.join()
    except KeyboardInterrupt:
        pass
    print("[程序结束] 所有线程已关闭")

if __name__ == "__main__":
    main()
