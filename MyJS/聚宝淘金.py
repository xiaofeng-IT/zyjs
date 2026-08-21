#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hmac
import hashlib
import base64
import json
import time
import uuid
import random
import requests
import os
import sys
from typing import Dict, Any, Optional, List
from requests.exceptions import ConnectionError, Timeout, RequestException
# ==================== 环境变量 ====================
# 设置方式：JB=token#oaid#userId#socks5_proxy（代理可留空）
def parse_jb_env():
    jb = os.environ.get('JB')
    if not jb:
        print("❌ 未找到环境变量 JB，请设置 JB=token#oaid#userId#socks5_proxy")
        sys.exit(1)
    parts = jb.split('#')
    if len(parts) != 4:
        print("❌ JB 格式错误，应为 token#oaid#userId#socks5_proxy")
        sys.exit(1)
    return parts[0], parts[1], parts[2], parts[3]

TOKEN, OAID, USER_ID, SOCKS5_PROXY = parse_jb_env()

SECRET_KEY = "FD1836D3D2BB1377727C6786B6F8CF90"
BASE_URL = "https://yx1565.fengkeji.cn"
VERSION = "1125"

AD_PLACEMENTS = {
    2: ("34193000100", "19", "横幅"),
    3: ("104113482",   "22", "插屏"),
    4: ("34193000030", "19", "信息流"),
}

TARGET_FORECAST_GOLD = 20000
MAX_AD_PER_DAY = 200
MAX_RETRIES = 3
RETRY_DELAY = 5

ECPM_MIN = 13400
ECPM_MAX = 21700

WATCH_AD_FAST_MIN = 6
WATCH_AD_FAST_MAX = 10
WATCH_AD_SLOW_MIN = 10
WATCH_AD_SLOW_MAX = 18

ROUND_INTERVAL_FAST_MIN = 8
ROUND_INTERVAL_FAST_MAX = 15
ROUND_INTERVAL_SLOW_MIN = 18
ROUND_INTERVAL_SLOW_MAX = 35

SPEED_CHANGE_PROBABILITY = 0.25
FAST_MODE_PROBABILITY = 0.50
CONSECUTIVE_FAST_MAX = 5
CONSECUTIVE_SLOW_MIN = 2

RANDOM_PAUSE_CHANCE = 0.10
RANDOM_PAUSE_MIN = 20
RANDOM_PAUSE_MAX = 60
MICRO_JITTER_RANGE = (0.5, 2.5)

SHA_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJEODZDRDY5N0ZBMDkxMDkyNUI2N0RFNkYwRUZGNTlCRjRBMzFEQkVBIn0.c2aLX4LTKLoHB7lfKa6RnYQqQFEpGYezrpVO0nKEN04"
TA_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJBT3RlclVybCJ9.K8ojsESrO2gsak3t7usaDktydPqvFYxKF671ylliid4"

def base64url_encode(data: bytes) -> str:
    b64 = base64.b64encode(data).decode('utf-8')
    return b64.rstrip('=').replace('+', '-').replace('/', '_')

def generate_jwt(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':'))
    payload_json = json.dumps(payload, separators=(',', ':'))

    header_b64 = base64url_encode(header_json.encode('utf-8'))
    payload_b64 = base64url_encode(payload_json.encode('utf-8'))

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def generate_tokena_jwt(token: str) -> str:
    return generate_jwt({"sub": token})


class HumanBehaviorSimulator:

    def __init__(self):
        self.is_fast_mode = random.random() < FAST_MODE_PROBABILITY
        self.consecutive_count = 0
        self.total_rounds = 0
        mode_name = "⚡ 快速模式" if self.is_fast_mode else "🐢 慢速模式"
        print(f"🎭 真人行为模拟器启动 | 初始速度: {mode_name}")

    def _maybe_switch_speed(self):
        should_switch = False

        if self.is_fast_mode:
            if self.consecutive_count >= CONSECUTIVE_FAST_MAX:
                should_switch = True
                reason = f"连续快速{self.consecutive_count}轮，触发疲劳机制"
            elif random.random() < SPEED_CHANGE_PROBABILITY:
                should_switch = True
                reason = "随机减速（模拟注意力分散）"
        else:
            if self.consecutive_count >= CONSECUTIVE_SLOW_MIN and random.random() < SPEED_CHANGE_PROBABILITY:
                should_switch = True
                reason = "随机加速（模拟重新集中注意力）"

        if should_switch:
            self.is_fast_mode = not self.is_fast_mode
            self.consecutive_count = 0
            mode_name = "⚡ 快速模式" if self.is_fast_mode else "🐢 慢速模式"
            print(f"  🔄 速度切换 → {mode_name} | 原因: {reason}")

    def get_watch_delay(self) -> float:
        self._maybe_switch_speed()
        self.consecutive_count += 1
        self.total_rounds += 1

        if self.is_fast_mode:
            delay = random.uniform(WATCH_AD_FAST_MIN, WATCH_AD_FAST_MAX)
        else:
            delay = random.uniform(WATCH_AD_SLOW_MIN, WATCH_AD_SLOW_MAX)

        delay += random.uniform(*MICRO_JITTER_RANGE)
        speed_tag = "⚡" if self.is_fast_mode else "🐢"
        print(f"  ⏱️  观看时长: {delay:.1f}秒 {speed_tag} (第{self.consecutive_count}轮/{self._get_mode_name()})")
        return delay

    def get_round_delay(self) -> float:
        if self.is_fast_mode:
            delay = random.uniform(ROUND_INTERVAL_FAST_MIN, ROUND_INTERVAL_FAST_MAX)
        else:
            delay = random.uniform(ROUND_INTERVAL_SLOW_MIN, ROUND_INTERVAL_SLOW_MAX)

        delay += random.uniform(*MICRO_JITTER_RANGE)
        speed_tag = "⚡" if self.is_fast_mode else "🐢"
        print(f"  ⏳ 轮次间隔: {delay:.1f}秒 {speed_tag}")
        return delay

    def maybe_random_pause(self) -> float:
        if random.random() < RANDOM_PAUSE_CHANCE:
            pause_time = random.uniform(RANDOM_PAUSE_MIN, RANDOM_PAUSE_MAX)
            print(f"  💭 随机走神！暂停 {pause_time:.0f}秒（模拟真人分心）")
            return pause_time
        return 0.0

    def apply_micro_jitter(self):
        jitter = random.uniform(*MICRO_JITTER_RANGE)
        time.sleep(jitter)

    def _get_mode_name(self) -> str:
        return "快速" if self.is_fast_mode else "慢速"

    def get_status(self) -> str:
        mode_name = self._get_mode_name()
        return f"总轮次: {self.total_rounds} | 当前模式: {mode_name}({self.consecutive_count}轮)"


class JuBaoTaoJin:

    def __init__(self):
        self.session = requests.Session()
        if SOCKS5_PROXY:
            self.session.proxies = {
                'http': SOCKS5_PROXY,
                'https': SOCKS5_PROXY,
            }
            print(f"🔌 使用 SOCKS5 代理: {SOCKS5_PROXY}")
        else:
            print("ℹ️ 未使用代理，直连网络")

        self.session.headers.update({
            "User-Agent": "okhttp/4.10.0",
            "version": VERSION,
            "Accept-Encoding": "gzip",
            "token": TOKEN,
        })
        self.tokena_jwt = generate_tokena_jwt(TOKEN)
        self.current_forecast_gold = 0
        self.ad_remaining = {2: None, 3: None, 4: None}
        self.ad_queue = []
        self.human_sim = HumanBehaviorSimulator()

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except (ConnectionError, Timeout, RequestException) as e:
                print(f"❌ 请求失败 (尝试 {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    print(f"⏳ 等待 {RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise

    def _post(self, path: str, data: Dict[str, str], extra_headers: Optional[Dict] = None) -> Dict[str, Any]:
        url = BASE_URL + path
        headers = self.session.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        resp = self._request_with_retry("POST", url, data=data, headers=headers)
        return resp.json()

    def _get(self, path: str, extra_headers: Optional[Dict] = None) -> Dict[str, Any]:
        url = BASE_URL + path
        headers = self.session.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        resp = self._request_with_retry("GET", url, headers=headers)
        return resp.json()

    def get_user_info(self) -> Dict[str, Any]:
        headers = {
            "sha": SHA_JWT,
            "tokena": self.tokena_jwt,
        }
        return self._get("/api/Member/GetUserinfo", extra_headers=headers)

    def get_notice(self) -> Dict[str, Any]:
        headers = {"sha1": SHA_JWT}
        return self._get("/api/adsdee/Notlst", extra_headers=headers)

    def request_ad(self, ad_type: int) -> Dict[str, Any]:
        data = {
            "ad_type": "1",
            "type": str(ad_type),
            "oaid": OAID,
        }
        return self._post("/api/Sigbom/GAdTye", data=data)

    def report_ad(self, ad_type: int, placement_id: str, network_id: str) -> Dict[str, Any]:
        eCPM = str(random.randint(ECPM_MIN, ECPM_MAX))
        load_id = str(uuid.uuid4())

        inner_payload = {
            "ad_type": "1",
            "dividenDs": "4",
            "eCPM": eCPM,
            "loadId": load_id,
            "networkId": network_id,
            "networkPlacementId": placement_id,
            "oaid": OAID,
            "placementId": placement_id,
            "sha": SHA_JWT,
            "type": str(ad_type),
            "version": VERSION
        }

        inner_json_str = json.dumps(inner_payload, separators=(',', ':'))
        sgin = generate_jwt({"sub": inner_json_str})

        data = {
            "oaid": OAID,
            "sgin": sgin,
            "tc": SHA_JWT,
            "ta": TA_JWT,
            "tb": sgin,
        }
        return self._post("/api/Pubqingqiu/Pdefgfuxdob", data=data)

    def update_forecast_gold_from_userinfo(self) -> int:
        try:
            resp = self.get_user_info()
            if resp.get("code") == 1:
                gold = int(resp["data"]["userinfo"].get("forecast_gold", 0))
                self.current_forecast_gold = gold
                return gold
            else:
                print(f"⚠️ 查询金币接口返回错误: {resp.get('msg')}")
                return self.current_forecast_gold
        except Exception as e:
            print(f"❌ 查询金币异常: {e}")
            return self.current_forecast_gold

    def get_available_ad_types(self) -> List[int]:
        available = []
        for ad_type, remaining in self.ad_remaining.items():
            if remaining is None or remaining > 0:
                available.append(ad_type)
        return available

    def update_remaining(self, ad_type: int, response: Dict[str, Any]):
        if response.get("code") == 1 and "data" in response:
            data = response["data"]
            if "number" in data:
                remaining = int(data["number"])
                self.ad_remaining[ad_type] = remaining
                print(f"✅ 更新 {AD_PLACEMENTS[ad_type][2]} 剩余次数: {remaining}")
        elif "暂无次数" in response.get("msg", ""):
            self.ad_remaining[ad_type] = 0
            print(f"⚠️ {AD_PLACEMENTS[ad_type][2]} 次数已用完，标记为0")

    def build_ad_queue(self):
        available = self.get_available_ad_types()
        if not available:
            self.ad_queue = []
            return
        shuffled = available.copy()
        random.shuffle(shuffled)
        self.ad_queue = shuffled
        print(f"🔄 生成新广告顺序: {[AD_PLACEMENTS[t][2] for t in self.ad_queue]}")

    def get_next_ad_type(self) -> Optional[int]:
        if not self.ad_queue:
            self.build_ad_queue()
        if self.ad_queue:
            return self.ad_queue.pop(0)
        else:
            return None

    def run(self, max_rounds: int = MAX_AD_PER_DAY, target_gold: int = TARGET_FORECAST_GOLD):
        print("\n" + "=" * 55)
        print("  聚宝淘金 v2.0（真人行为模拟版）")
        print("=" * 55)
        print(f"👤 用户ID: {USER_ID}")
        print(f"📱 OAID: {OAID}")
        print(f"🎯 目标金币: {target_gold}")
        print(f"🔄 最大轮次: {max_rounds}")
        print("-" * 55)

        init_gold = self.update_forecast_gold_from_userinfo()
        print(f"💰 当前金币 (forecast_gold): {init_gold}")
        if init_gold >= target_gold:
            print("🎉 当前金币已达到目标，无需执行。")
            return

        round_count = 0
        total_earned = 0

        print(f"\n🛡️ 开始执行... | 行为模拟器状态: {self.human_sim.get_status()}\n")

        for i in range(max_rounds):
            if self.current_forecast_gold >= target_gold:
                print(f"\n🎯 当前金币 {self.current_forecast_gold} 已达到目标 {target_gold}，停止脚本。")
                break

            ad_type = self.get_next_ad_type()
            if ad_type is None:
                print("\n❌ 没有可用的广告类型，停止脚本。")
                break

            placement_id, network_id, ad_name = AD_PLACEMENTS[ad_type]
            print(f"\n{'='*55}")
            print(f"  📺 第 {i+1} 轮 | 广告类型: {ad_name} (type={ad_type})")
            print(f"{'='*55}")

            try:
                self.human_sim.apply_micro_jitter()

                ad_req = self.request_ad(ad_type)
                self.update_remaining(ad_type, ad_req)

                if ad_req.get("code") != 1:
                    print(f"❌ 请求广告失败: {ad_req.get('msg')}")
                    if "暂无次数" in ad_req.get("msg", ""):
                        self.ad_remaining[ad_type] = 0
                        self.ad_queue = []

                    fail_delay = self.human_sim.get_round_delay()
                    print(f"⏳ 等待 {fail_delay:.1f} 秒后继续...")
                    time.sleep(fail_delay)
                    continue

                ad_data = ad_req.get("data", {})
                remaining = ad_data.get('number', 0)
                print(f"✅ 广告请求成功: {ad_data.get('adname')} | 剩余次数: {remaining}")

                overtime = ad_data.get('overtime', 0)
                if overtime > 0:
                    print(f"⏳ 服务器要求冷却等待 {overtime} 秒...")
                    time.sleep(overtime + random.uniform(1, 3))

            except Exception as e:
                print(f"❌ 请求广告异常: {e}，跳过本轮")
                err_delay = self.human_sim.get_round_delay()
                time.sleep(err_delay)
                continue

            watch_delay = self.human_sim.get_watch_delay()
            print(f"👀 正在模拟观看广告...")

            watch_segments = 3
            segment_time = watch_delay / watch_segments
            for seg in range(watch_segments):
                time.sleep(segment_time)
                progress_pct = int((seg + 1) / watch_segments * 100)
                bar = "█" * (seg + 1) + "░" * (watch_segments - seg - 1)
                print(f"  [{bar}] 观看进度 {progress_pct}%")

            pause_time = self.human_sim.maybe_random_pause()
            if pause_time > 0:
                time.sleep(pause_time)

            before_gold = self.current_forecast_gold
            try:
                self.human_sim.apply_micro_jitter()

                print(f"📤 正在上报广告观看完成...")
                report_resp = self.report_ad(ad_type, placement_id, network_id)

                if report_resp.get("code") != 1:
                    print(f"❌ 上报失败: {report_resp.get('msg')}")
                else:
                    print(f"✅ 上报成功！等待服务器结算...")
                    time.sleep(random.uniform(2, 4))

                    after_gold = self.update_forecast_gold_from_userinfo()
                    earned = after_gold - before_gold
                    total_earned += earned
                    round_count += 1

                    print(f"💰 金币变化: {before_gold} → {after_gold} (+{earned}) | 累计赚取: {total_earned}")

                    if after_gold >= target_gold:
                        print(f"\n🎉🎉🎉 已达到目标金币 {target_gold}！脚本结束 🎉🎉🎉\n")
                        break

            except Exception as e:
                print(f"❌ 上报异常: {e}，本轮作废，继续下一轮")

            round_delay = self.human_sim.get_round_delay()
            print(f"⏳ 等待 {round_delay:.1f} 秒后开始下一轮...\n")
            time.sleep(round_delay)

        final_gold = self.current_forecast_gold
        print("\n" + "=" * 55)
        print("  📊 执行统计报告")
        print("=" * 55)
        print(f"  ✅ 成功上报次数: {round_count}")
        print(f"  💰 总赚取金币:   {total_earned}")
        print(f"  💎 最终金币:     {final_gold}")
        print(f"  🎭 行为模拟器:   {self.human_sim.get_status()}")
        print("=" * 55)

if __name__ == "__main__":
    bot = JuBaoTaoJin()
    bot.run()
