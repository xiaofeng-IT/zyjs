#!/usr/bin/env python3
"""
酷我音乐任务系统 v1.0 - 客户端
功能: 签到 + 听歌时长上报 + 听歌金币领取(含翻倍) + 签到广告 + 开宝箱 + 宝箱弹窗
      + 抽奖(免费+视频) + 收藏歌曲 + 整点打卡
      + 今日累计奖励 + 视频广告 + 整点领金币广告 + 惊喜广告
      + 种树摇钱(浇水/摇树/阶段奖励)
      + 迎财神(签到+免费抽奖+周结算)
      + 多账号支持 + 青龙通知推送

环境变量(必填):
  KUWO_ACCOUNTS          账号密码，格式: 手机号1#密码1 (多账号换行分隔)
  KUWO_AUTH_KEY           授权码(联系作者获取,默认已内置授权码)

环境变量(选填):
  KUWO_PROXY              代理配置,填IP:PORT直接代理 或 填完整API地址自动提取
  KUWO_TREE_DISABLE       设为1关闭种树摇钱模块
  KUWO_CAISHEN_DISABLE    设为1关闭迎财神模块


★酷我提现地址：https://tool.zzcx.qzz.io/
★按需使用
cron: 10 8 * * *
"""

import os, sys, json, urllib.request, urllib.error

# ============ 服务端地址(勿修改) ============
SERVER_URL = os.environ.get("KUWO_SERVER", "https://task.zzcx.qzz.io")

# ============ 从环境变量读取配置 ============
# 授权码: 联系作者获取,用于验证身份(必填)
AUTH_KEY = os.environ.get("KUWO_AUTH_KEY", "hello158")
# 账号密码: 格式 手机号#密码, 多账号换行分隔(必填)
ACCOUNTS = os.environ.get("KUWO_ACCOUNTS", "")
# 代理: 填IP:PORT直接用, 填http://开头的API地址自动提取(选填)
PROXY = os.environ.get("KUWO_PROXY", "")
# 设为1关闭种树摇钱模块(选填,默认开启)
TREE_DISABLE = os.environ.get("KUWO_TREE_DISABLE", "")
# 设为1关闭迎财神模块(选填,默认开启)
CAISHEN_DISABLE = os.environ.get("KUWO_CAISHEN_DISABLE", "")

# ============ 青龙通知(双保险: 优先notify模块, 备用API) ============
def send_ql_notify(title, content):
    """发送青龙通知: 优先用notify.send(task命令自动注入推送配置), 失败则走API"""
    # 方式1: 标准notify模块(青龙task命令运行时自动注入推送环境变量)
    try:
        os.environ["HITOKOTO"] = "false"  # 关闭一言防DNS崩溃
        import importlib, io, contextlib
        sys.path.insert(0, "/ql/data/scripts")
        notify = importlib.import_module("notify")
        # 捕获stdout检测是否真的推送成功
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            notify.send(title, content)
        output = buf.getvalue()
        print(output, end="")  # 原样输出
        if "推送成功" in output:
            return True
    except Exception:
        pass
    # 方式2: API方式(兜底)
    try:
        auth_path = "/ql/data/config/auth.json"
        if not os.path.exists(auth_path):
            return False
        with open(auth_path) as f:
            auth = json.loads(f.read())
        login_data = json.dumps({"username": auth["username"], "password": auth["password"]}).encode()
        login_req = urllib.request.Request(
            "http://127.0.0.1:5700/api/user/login", data=login_data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        token = json.loads(urllib.request.urlopen(login_req, timeout=10).read()).get("data", {}).get("token", "")
        if not token:
            return False
        notify_data = json.dumps({"title": title, "content": content}).encode()
        notify_req = urllib.request.Request(
            "http://127.0.0.1:5700/api/system/notify", data=notify_data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="PUT"
        )
        resp = json.loads(urllib.request.urlopen(notify_req, timeout=15).read())
        return resp.get("code") == 200
    except Exception:
        return False

def main():
    if not AUTH_KEY:
        print("❌ 未设置授权码,请添加环境变量 KUWO_AUTH_KEY")
        sys.exit(1)
    if not ACCOUNTS:
        print("❌ 未设置账号,请添加环境变量 KUWO_ACCOUNTS")
        sys.exit(1)

    # 构建请求
    payload = json.dumps({
        "auth_key": AUTH_KEY,
        "accounts": ACCOUNTS,
        "proxy": PROXY,
        "tree_disable": TREE_DISABLE,
        "caishen_disable": CAISHEN_DISABLE,
    }).encode("utf-8")

    url = f"{SERVER_URL.rstrip('/')}/run"
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "KuwoClient/7.0")

    print("🔗 连接服务器...")
    all_lines = []

    try:
        with urllib.request.urlopen(req, timeout=960) as resp:
            # 检查是否SSE流
            ct = resp.headers.get("Content-Type", "")
            if "event-stream" not in ct:
                # 非流式 = 错误响应
                body = resp.read().decode("utf-8")
                try:
                    err = json.loads(body)
                    print(f"❌ {err.get('error', body)}")
                except Exception:
                    print(f"❌ {body}")
                sys.exit(1)

            print("✅ 已连接\n")
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data:"):
                    content = line[5:]
                    if content == "[DONE]":
                        break
                    if content == "heartbeat":
                        continue
                    print(content)
                    all_lines.append(content)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            print(f"❌ {err.get('error', body)}")
        except Exception:
            print(f"❌ HTTP {e.code}: {body[:200]}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ 无法连接服务器: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        sys.exit(1)

    # 青龙通知推送 - 识别特殊标记，直接透传（支持多账号）
    if all_lines:
        # 查找所有 >>>NOTIFY_START<<< 和 >>>NOTIFY_END<<< 标记对
        notify_blocks = []
        in_notify = False
        current_block = []
        
        for line in all_lines:
            if line == ">>>NOTIFY_START<<<":
                in_notify = True
                current_block = []
                continue
            elif line == ">>>NOTIFY_END<<<":
                in_notify = False
                if current_block:
                    notify_blocks.append(current_block)
                continue
            elif in_notify:
                current_block.append(line)
        
        # 如果找到标记，合并所有账号的推送内容
        if notify_blocks:
            # 第一个block的第一行是标题
            notify_title = notify_blocks[0][0] if notify_blocks[0] else "酷我音乐 · 每日任务"
            # 合并所有block的内容（跳过每个block的标题行）
            all_notify_lines = []
            for block in notify_blocks:
                if block:
                    all_notify_lines.extend(block[1:])  # 跳过标题行
                all_notify_lines.append("")  # 账号间空行
            summary = "\n".join(all_notify_lines).strip()
        else:
            # 回退：关键词过滤
            notify_title = "酷我音乐 · 每日任务"
            summary_lines = []
            in_summary = False
            for line in all_lines:
                if "📢" in line:
                    in_summary = True
                if in_summary:
                    summary_lines.append(line)
            if not summary_lines:
                for line in all_lines:
                    if any(k in line for k in ["📈 本次", "💰 余额", "❌ 登录失败", "🌳 种树摇钱:", "📱 账号"]):
                        summary_lines.append(line)
            if not summary_lines:
                summary_lines = all_lines[-20:]
            summary = "\n".join(summary_lines)
        
        if send_ql_notify(notify_title, summary):
            print("\n📨 青龙通知已发送")
        else:
            print("\n⚠️ 青龙通知未发送")


if __name__ == "__main__":
    main()
