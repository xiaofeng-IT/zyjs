#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米有品/商城 —— 签到 & 做任务领奖 (青龙面板可执行)
====================================================================
青龙使用方法
--------------------------------------------------------------------
1. 依赖:  pip install requests   (青龙 -> 依赖管理 -> Python3 -> 新建 requests)
2. 环境变量(青龙 -> 环境变量):
   名称: MI_YOUPIN_COOKIE
   值  : 抓包拿到的完整 Cookie 串(至少含 serviceToken; cUserId; userId)
   多账号: 用 & 或换行分隔多份 Cookie
   (可选) MI_YOUPIN_ACTID  : 活动ID,不填用脚本内置的当前签到活动
3. 定时:  建议每天 0 9 * * *  (早上9点)
====================================================================
"""
import os
import sys
import json
import time

try:
    import requests
except ImportError:
    print("艹,缺 requests 库,青龙依赖管理里装一个:requests")
    sys.exit(1)


# ============================================================
# 配置区(一般不用改,活动换了再改 ACT_ID / TASKS)
# ============================================================

# 主签到活动 ID(抓包来的;活动过期了换成新的,或用环境变量 MI_YOUPIN_ACTID 覆盖)
DEFAULT_ACT_ID = "6706c0695404a23dfb5b2cab"

# mtop 网关域名(无签名直连)
HOST = "https://shop-api.retail.mi.com"

# 任务表:{taskId, taskType}  —— 来自 a.hl.mi.com HAR 抓包
# do 只要 taskId+actId;done 要 taskToken(do返回)+actId+taskType
# taskType: 110=签到, 200=逛/浏览类, 211=浏览商品计时
TASKS = [
    {"taskId": "6706c0695243011f230d465d", "taskType": 110, "name": "每日签到"},
    {"taskId": "68d5f33c8339d57994fead32", "taskType": 200, "name": "会员任务"},
    {"taskId": "695496a31c94bc3148d28ead", "taskType": 200, "name": "逛会员得米金"},
    {"taskId": "695496a31c94bc3148d28eaf", "taskType": 200, "name": "逛新品得米金"},
    {"taskId": "69cddfb1b4d4ed788a055f4f", "taskType": 200, "name": "逛K90"},
    {"taskId": "69fd3eb203c89749f7e0cf1f", "taskType": 211, "name": "浏览商品10s"},
    {"taskId": "69fd40bbf167a6340ad40f05", "taskType": 200, "name": "逛15s得现金"},
    {"taskId": "6a339e3f88e0024f8561ad52", "taskType": 200, "name": "逛白家电"},
]

REQ_TIMEOUT = 15
SLEEP_BETWEEN = 1.5   # 每个任务间隔,别把服务器当傻子狂打


# ============================================================
# 工具函数
# ============================================================

def log(msg):
    print(msg, flush=True)


def parse_accounts():
    """从环境变量读多账号 cookie,& 或换行分隔"""
    raw = os.environ.get("MI_YOUPIN_COOKIE", "").strip()
    if not raw:
        log("艹,没配 MI_YOUPIN_COOKIE 环境变量,这脚本是要老王我变魔术?")
        sys.exit(1)
    parts = []
    for chunk in raw.replace("\n", "&&").split("&&"):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    # 兼容单账号里本身带 & 的情况:如果只有一份且含 serviceToken,就当一个
    if len(parts) == 1:
        return parts
    # 多份:每份都得像个完整 cookie(含 serviceToken)
    accounts = [p for p in parts if "serviceToken" in p]
    return accounts or [raw]


def build_headers(cookie):
    return {
        "Content-Type": "application/json",
        "x-user-agent": "channel/mishop platform/mishop.android",
        "equipmenttype": "3",
        "DToken": "",
        "Cookie": cookie,
        "referer": HOST + "/",
        "User-Agent": "okhttp/3.12.3",
    }


def get_userid(cookie):
    for kv in cookie.split(";"):
        kv = kv.strip()
        if kv.startswith("userId="):
            return kv[len("userId="):]
    return "未知"


def mtop_post(session, cookie, path, *args):
    """mtop 统一 POST,body=[{},*args]"""
    url = HOST + path
    body = json.dumps([{}, *args], ensure_ascii=False)
    r = session.post(url, data=body.encode("utf-8"),
                     headers=build_headers(cookie), timeout=REQ_TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"code": -1, "_raw": r.text[:200], "_status": r.status_code}


# ============================================================
# 业务逻辑
# ============================================================

def do_task(session, cookie, act_id, task):
    """单个任务:do 取 token -> done 领奖"""
    tid = task["taskId"]
    ttype = task["taskType"]
    name = task.get("name") or tid

    # 第一步:do 换取 taskToken
    r1 = mtop_post(session, cookie, "/mtop/mf/act/infinite/do",
                   {"taskId": tid, "actId": act_id})
    code1 = r1.get("code")
    token = (r1.get("data") or {}).get("taskToken")
    if code1 in (401, 999999999301, 999999999302):
        return "token_invalid"
    if not token:
        log(f"  [失败] {name} do未拿到token: code={code1} msg={r1.get('message')}")
        return "fail"

    time.sleep(SLEEP_BETWEEN)

    # 第二步:done
    r2 = mtop_post(session, cookie, "/mtop/mf/act/infinite/done",
                   {"taskToken": token, "actId": act_id, "taskType": ttype})
    code2 = r2.get("code")
    if code2 in (401, 999999999301, 999999999302):
        return "token_invalid"
    if code2 == 0:
        awards = (r2.get("data") or {}).get("awardList") or []
        if awards:
            desc = ", ".join(
                f"{a.get('awardName', '奖励')}x{a.get('awardValue', '')}" for a in awards
            )
            log(f"  [领取] {name} -> {desc}")
        else:
            log(f"  [完成] {name} (无奖励或已领)")
        return "ok"
    else:
        log(f"  [失败] {name} done: code={code2} msg={r2.get('message')}")
        return "fail"


def run_account(idx, cookie):
    uid = get_userid(cookie)
    log(f"\n========== 账号#{idx} (userId={uid}) ==========")
    act_id = os.environ.get("MI_YOUPIN_ACTID", "").strip() or DEFAULT_ACT_ID
    log(f"活动ID: {act_id}")

    session = requests.Session()

    ok = fail = 0
    for task in TASKS:
        res = do_task(session, cookie, act_id, task)
        if res == "token_invalid":
            log("  !! serviceToken 失效,这账号 cookie 过期了,重新抓包更新环境变量")
            break
        ok += (res == "ok")
        fail += (res == "fail")
        time.sleep(SLEEP_BETWEEN)

    log(f"账号#{idx} 小结: 成功{ok} 失败{fail} (共{len(TASKS)}个任务)")


def main():
    log("===== 小米有品 签到&做任务领奖 =====")
    accounts = parse_accounts()
    log(f"共 {len(accounts)} 个账号")
    for i, cookie in enumerate(accounts, 1):
        try:
            run_account(i, cookie)
        except Exception as e:
            log(f"账号#{i} 跑挂了: {e}")
        time.sleep(2)
    log("\n===== 全部跑完 =====")


if __name__ == "__main__":
    main()
