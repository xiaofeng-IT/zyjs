#!/usr/bin/env python3
"""
58同城青龙脚本：
功能：签到，浏览

环境变量：
- wbtc_cokie
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


RIGHTS_BASE = "https://rightsplatform.58.com"
TASK_BASE = "https://taskframe.58.com"

IOS_CHOICES = ["18_7", "18_6", "18_5", "18_4", "17_7", "17_6"]
MOBILE_CHOICES = ["15E148", "16A366", "17A577", "18A8395"]
APP_CHOICES = ["13.47.1", "13.47.0", "13.46.2", "13.46.1", "13.45.8"]


@dataclass
class Account:
    name: str
    cookie: str


class Wuba58Client:
    def __init__(self, account: Account, ua: str, timeout: float, delay: float) -> None:
        self.account = account
        self.timeout = timeout
        self.delay = delay

        self.s = requests.Session()
        self.s.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "User-Agent": ua,
                "Origin": RIGHTS_BASE,
                "Referer": f"{RIGHTS_BASE}/",
                "Cookie": normalize_cookie(account.cookie),
            }
        )

    def _json_request(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> Dict:
        r = self.s.request(method=method, url=url, params=params, timeout=self.timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception as e:
            snippet = (r.text or "")[:200]
            raise RuntimeError(f"non-json response: {snippet}") from e

    def get_user(self) -> Dict:
        return self._json_request(
            "GET", f"{RIGHTS_BASE}/v3/user/", params={"needSignDetail": "true"}
        )

    def do_sign(self) -> Dict:
        return self._json_request("POST", f"{RIGHTS_BASE}/v3/sign")

    def get_dolist(self, source: str = "") -> Dict:
        return self._json_request(
            "GET",
            f"{TASK_BASE}/web/task/dolist",
            params={"sceneId": 56, "openpush": 1, "source": source},
        )

    def dotask(self, task_id: str, task_data: int) -> Dict:
        ts = now_ms()
        params = {
            "timestamp": ts,
            "sign": md5_hex(f"{ts}{task_id}"),
            "taskId": task_id,
            "taskData": task_data,
            "needReward": 1,
        }
        return self._json_request("GET", f"{TASK_BASE}/web/task/dotask", params=params)

    def reward(self, task_id: str) -> Dict:
        ts = now_ms()
        params = {
            "timestamp": ts,
            "sign": md5_hex(f"{ts}{task_id}"),
            "taskId": task_id,
        }
        return self._json_request("GET", f"{TASK_BASE}/web/task/reward", params=params)

    def run(self) -> int:
        before_user = self.get_user()
        user_id = safe_int(before_user.get("result", {}).get("userId"))
        show_name = self.account.name
        if show_name.startswith("acc") and user_id > 0:
            show_name = str(user_id)
        print(f"账号==》{show_name}")

        before_points = safe_int(before_user.get("result", {}).get("usablePoints"))
        sign_status = safe_int(
            before_user.get("result", {}).get("signDetail", {}).get("signStatus")
        )

        if sign_status == 1:
            print("签到==》今日已签到（无需重复）")
        else:
            sign_resp = self.do_sign()
            if sign_resp.get("code") == 0:
                award = sign_resp.get("result", {}).get("awardDesc", "")
                print(f"签到==》成功🟢（{award}）")
            else:
                msg = f"code={sign_resp.get('code')} msg={sign_resp.get('message')}"
                print(f"签到==》失败🔴（{msg}）")

        do_list = self.get_dolist().get("result", {}).get("taskList", [])
        all_tasks: List[Dict] = [t for t in do_list if t.get("itemId")]
        actionable: List[Dict] = []
        for t in all_tasks:
            status = safe_int(t.get("status"))
            done_cnt = safe_int(t.get("taskDoneCount"))
            total_cnt = safe_int(t.get("taskTotalCount"))
            if status == 2:
                continue
            if total_cnt > 0 and done_cnt >= total_cnt:
                continue
            if status in (0, 1):
                actionable.append(t)

        done_count = 0
        reward_count = 0
        fail_count = 0
        blocked_count = 0
        task_logs: List[str] = []
        for t in all_tasks:
            name = str(t.get("itemName") or t.get("itemId"))
            status = safe_int(t.get("status"))
            done_cnt = safe_int(t.get("taskDoneCount"))
            total_cnt = safe_int(t.get("taskTotalCount"))
            if status == 2 or (total_cnt > 0 and done_cnt >= total_cnt):
                task_logs.append(f"任务==》{name}（今日已完成，无需重复）")

        for t in actionable:
            task_id = str(t.get("itemId"))
            name = str(t.get("itemName") or task_id)
            status = safe_int(t.get("status"))

            try:
                if status == 1:
                    time.sleep(max(2.5, self.delay / 2) + random.uniform(0.8, 1.8))
                    resp = self.reward(task_id)
                    if resp.get("code") == 104:
                        blocked_count += 1
                        task_logs.append(
                            f"任务==》{name}（失败🔴）频率异常，停止后续任务"
                        )
                        break
                    ok = resp.get("code") == 0 and bool(resp.get("result"))
                    if ok:
                        reward_count += 1
                        done_count += 1
                        task_logs.append(f"任务==》{name}（成功🟢）")
                    else:
                        fail_count += 1
                        task_logs.append(f"任务==》{name}（失败🔴）{brief(resp)}")
                    time.sleep(self.delay + random.uniform(0.8, 2.6))
                    continue

                task_data = pick_task_data(t)
                if task_data <= 0:
                    fail_count += 1
                    task_logs.append(f"任务==》{name}（失败🔴）taskData无效")
                    continue

                time.sleep(max(self.delay, float(task_data)) + random.uniform(1.2, 3.8))
                do_resp = self.dotask(task_id, task_data)
                if do_resp.get("code") == 104:
                    blocked_count += 1
                    task_logs.append(f"任务==》{name}（失败🔴）频率异常，停止后续任务")
                    break
                do_ok = do_resp.get("code") == 0 and bool(do_resp.get("result"))
                if not do_ok:
                    fail_count += 1
                    task_logs.append(
                        f"任务==》{name}（失败🔴）做任务失败：{brief(do_resp)}"
                    )
                    time.sleep(self.delay + random.uniform(0.8, 2.2))
                    continue

                time.sleep(max(2.0, self.delay / 2) + random.uniform(0.6, 1.8))
                rw_resp = self.reward(task_id)
                if rw_resp.get("code") == 104:
                    blocked_count += 1
                    task_logs.append(f"任务==》{name}（失败🔴）频率异常，停止后续任务")
                    break
                rw_ok = rw_resp.get("code") == 0 and bool(rw_resp.get("result"))
                if rw_ok:
                    reward_count += 1
                    done_count += 1
                    task_logs.append(f"任务==》{name}（成功🟢）")
                else:
                    fail_count += 1
                    task_logs.append(
                        f"任务==》{name}（失败🔴）领奖失败：{brief(rw_resp)}"
                    )

                time.sleep(self.delay + random.uniform(1.0, 2.8))

            except Exception as e:
                fail_count += 1
                task_logs.append(f"任务==》{name}（失败🔴）异常：{e}")

        after_user = self.get_user()
        after_points = safe_int(after_user.get("result", {}).get("usablePoints"))
        delta = after_points - before_points

        if task_logs:
            for line in task_logs:
                print(line)
        else:
            print("任务==》今日任务已完成，无需重复")

        print(
            f"汇总：今日共获得 {delta} 积分（任务成功{done_count}，失败{fail_count}，限频{blocked_count}）"
        )

        return 0 if fail_count == 0 else 1


def pick_task_data(task: Dict) -> int:
    cc = task.get("completionCondition") or {}
    times = cc.get("times") if isinstance(cc, dict) else None
    if times is not None:
        return safe_int(times)

    tc = task.get("taskCount")
    if tc is not None:
        return safe_int(tc)

    return 1


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def now_ms() -> int:
    return int(time.time() * 1000)


def safe_int(v) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def brief(resp: Dict) -> str:
    return (
        f"代码={resp.get('code')} 信息={resp.get('message')} 结果={resp.get('result')}"
    )


def normalize_cookie(cookie: str) -> str:
    c = cookie.strip()
    if c.lower().startswith("cookie:"):
        c = c.split(":", 1)[1].strip()
    return c


def parse_accounts(raw: str) -> List[Account]:
    raw = (raw or "").strip()
    if not raw:
        return []

    if raw.startswith("["):
        arr = json.loads(raw)
        out: List[Account] = []
        for i, x in enumerate(arr, start=1):
            if isinstance(x, str):
                out.append(Account(name=f"acc{i}", cookie=x.strip()))
            elif isinstance(x, dict) and x.get("cookie"):
                out.append(
                    Account(
                        name=str(x.get("name") or f"acc{i}"),
                        cookie=str(x["cookie"]).strip(),
                    )
                )
        return out

    if "\n" in raw:
        parts = [p.strip() for p in raw.splitlines() if p.strip()]
    elif "###" in raw:
        parts = [p.strip() for p in raw.split("###") if p.strip()]
    else:
        parts = [raw]

    out: List[Account] = []
    for i, part in enumerate(parts, start=1):
        if "#" in part:
            n, c = part.split("#", 1)
            if "=" in c:
                out.append(Account(name=n.strip() or f"acc{i}", cookie=c.strip()))
                continue
        out.append(Account(name=guess_account_name(part, f"acc{i}"), cookie=part))
    return out


def read_cookie_env() -> str:
    v = os.getenv("wbtc_cookie")
    return v.strip() if v else ""


def guess_account_name(cookie: str, fallback: str) -> str:
    m = parse_cookie_map(cookie)
    if m.get("58uname"):
        return m["58uname"]
    if m.get("username"):
        return m["username"]

    if m.get("58cooper"):
        inner = parse_inner_kv(m["58cooper"])
        if inner.get("username"):
            return inner["username"]
        if inner.get("userid"):
            return inner["userid"]

    if m.get("www58com"):
        inner = parse_inner_kv(m["www58com"])
        if inner.get("UserName"):
            return inner["UserName"]
        if inner.get("UserID"):
            return inner["UserID"]

    if m.get("PPU"):
        inner = parse_inner_kv(m["PPU"])
        if inner.get("UN"):
            return inner["UN"]
        if inner.get("UID"):
            return inner["UID"]

    if m.get("uid"):
        return m["uid"]
    return fallback


def parse_cookie_map(cookie: str) -> Dict[str, str]:
    c = normalize_cookie(cookie)
    out: Dict[str, str] = {}
    for seg in c.split(";"):
        seg = seg.strip()
        if not seg or "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        out[k.strip()] = v.strip().strip('"')
    return out


def parse_inner_kv(s: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for kv in s.split("&"):
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        out[k] = v
    return out


def build_random_ua() -> str:
    ios = random.choice(IOS_CHOICES)
    mobile = random.choice(MOBILE_CHOICES)
    app = random.choice(APP_CHOICES)
    return (
        f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios} like Mac OS X) "
        f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/{mobile} WUBA/{app}"
    )


def main() -> int:
    raw = read_cookie_env()
    if not raw:
        print(
            "缺少环境变量：wbtc_cookie\n"
            "示例：wbtc_cookie='58cooper=...; PPU=...; www58com=...; ...'"
        )
        return 2

    ua = os.getenv("58_ua", "").strip() or build_random_ua()
    timeout = float(os.getenv("58_timeout", "12"))
    delay = float(os.getenv("58_delay", "12"))

    accounts = parse_accounts(raw)
    if not accounts:
        print("环境变量解析失败：未找到有效账号")
        return 2

    exit_code = 0
    for acc in accounts:
        try:
            c = Wuba58Client(acc, ua=ua, timeout=timeout, delay=delay)
            rc = c.run()
            if rc != 0:
                exit_code = 1
        except Exception as e:
            exit_code = 1
            print(f"===== [{acc.name}] 致命异常 =====")
            print(e)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
