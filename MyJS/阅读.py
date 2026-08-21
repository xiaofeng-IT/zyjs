# -*- coding: utf-8 -*-
"""
cron: 15 7,12,18 * * *
new Env('小星星全自动阅读')
"""

"""
==============================================================================
                    【小阅阅全自动阅读】
==============================================================================
入口：http://k381fqs.o2m49.asia/xiaoxinxin/wode2/c1835c58fb62f21e20d3638774e8a860
一、环境变量配置说明    
    1. 必须配置的环境变量：
       - 名称：xyy_cookie
         说明：抓包获取的 Cookie (主要是 ysmuid 字段)
         示例：ysmuid=2b5db1a0d9dc405e6c2496c1d24e255c

       - 名称：xyy_unionid
         说明：抓包获取的账号用户唯一标识 unionid
         示例：oZdBp0y-rscfOkSiKiRvT7SMIsn8

    2. 可选配置的环境变量：
       - 名称：xyy_domain
         说明：目标接口的主域名（如域名变更可在此替换），默认：http://c4dfacd.ohqnjl.asia

       - 名称：xyy_max_read
         说明：单次运行每个账号最大阅读文章篇数限制，默认：30

二、多账号配置说明：
    支持在同一个环境变量中配置多个账号，账号之间使用 "&" 或 "@" 或 "换行" 分隔。
    注意：xyy_cookie 与 xyy_unionid 中的账号顺序必须一一对应！

    示例 1（多账号用 & 分隔）：
       xyy_cookie  : ysmuid=cookie_user1&ysmuid=cookie_user2
       xyy_unionid : unionid_user1&unionid_user2

    示例 2（新增多变量，同名环境变量多条记录）：
       青龙面板支持添加多个同名变量 `xyy_cookie` 和 `xyy_unionid`，脚本会自动依次匹配组合。

==============================================================================
"""

import os
import sys
import time
import random
import urllib.parse
import requests

# Windows 控制台编码兼容适配及实时日志刷新 (防止缓冲区积压)
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# 覆盖 print 函数，强制设置 flush=True 即时刷新日志
_original_print = print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _original_print(*args, **kwargs)

# 尝试导入青龙面板通用通知模块
try:
    from notify import send
except ImportError:
    try:
        from ql_sendNotify import send
    except ImportError:
        def send(title, content):
            print(f"\n[消息通知] {title}\n{content}\n")

DEFAULT_DOMAIN = "http://c4dfacd.ohqnjl.asia"
DEFAULT_MAX_READ = 30
READ_DURATION_MIN = 30
READ_DURATION_MAX = 60
MAX_CONTINUOUS_ERRORS = 5

def parse_env_list(env_name):
    """解析青龙环境变量（支持多变量格式、&、@、换行等分隔符）"""
    val = os.getenv(env_name, "").strip()
    if not val:
        return []
    
    for sep in ["\n", "&", "@", ";"]:
        val = val.replace(sep, ",")
    
    items = [item.strip() for item in val.split(",") if item.strip()]
    return items

def get_accounts():
    """获取并解析所有账户配置"""
    cookies = parse_env_list("xyy_cookie")
    unionids = parse_env_list("xyy_unionid")
    
    if not cookies or not unionids:
        print("❌ 未检测到正确的环境变量设置！")
        print("请检查青龙面板环境变量中是否已添加 `xyy_cookie` 和 `xyy_unionid`。")
        return []
        
    if len(cookies) != len(unionids):
        print(f"⚠️ 警告: xyy_cookie ({len(cookies)}个) 与 xyy_unionid ({len(unionids)}个) 数量不一致，将自动匹配较短者。")
        
    accounts = []
    for i in range(min(len(cookies), len(unionids))):
        accounts.append({
            "index": i + 1,
            "cookie": cookies[i],
            "unionid": unionids[i]
        })
    return accounts

def get_headers(cookie_str):
    """构建标准微信请求头"""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 16; V2405A Build/BP2A.250605.031.A3_V000L1; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 "
            "XWEB/1460217 MMWEBSDK/20260502 MMWEBID/8073 REV/580c5b91ffa4b88fe7e562d440e82104b327a000 "
            "MicroMessenger/8.0.76.3140(0x28004C31) WeChat/arm64 Weixin NetType/5G Language/zh_CN ABI/arm64"
        ),
        "X-Requested-With": "com.tencent.mm",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": cookie_str if "ysmuid=" in cookie_str else f"ysmuid={cookie_str}"
    }

def get_user_status(session, host_domain, unionid, headers):
    """查询当前用户金币与已读数量（调用包含阅读收益数据的 /gold 接口）"""
    url = f"{host_domain}/xiaoxinxin/gold"
    params = {
        "unionid": unionid,
        "time": int(time.time() * 1000)
    }
    try:
        res = session.get(url, params=params, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print(f"❌ 查询账号状态异常: {e}")
        return None

def process_single_read(session, host_domain, headers, unionid, read_idx, max_read):
    """执行单篇文章阅读流程并返回增加的金币及状态"""
    print(f"\n📖 [文章 {read_idx}/{max_read}] 开始获取阅读任务...")
    
    # 步骤 1: 向 duliks 发送请求获取任务 RID 与跳转子域名
    duliks_url = f"{host_domain}/xiaoxinxin/duliks"
    post_headers = headers.copy()
    post_headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": host_domain,
        "Referer": f"{host_domain}/xiaoxinxin/home.html?ysi=0"
    })
    
    try:
        res_duliks = session.post(duliks_url, data={"unionid": unionid}, headers=post_headers, timeout=10).json()
    except Exception as e:
        print(f"❌ [步骤1] 获取任务网络异常: {e}")
        return False, 0, f"网络异常: {e}"

    if res_duliks.get("errcode") != 0 or not res_duliks.get("data", {}).get("domain"):
        msg = res_duliks.get("msg", "未获取到任务域名")
        print(f"⚠️ [步骤1] 任务响应提示: {msg}")
        return False, 0, msg

    domain_url = res_duliks["data"]["domain"]
    parsed = urllib.parse.urlparse(domain_url)
    base_host = f"{parsed.scheme}://{parsed.netloc}"
    query_params = urllib.parse.parse_qs(parsed.query)
    rid = query_params.get("rid", [""])[0]

    if not rid:
        print("❌ [步骤1] 未能提取到有效的 RID 参数")
        return False, 0, "无效RID"

    print(f"  ├─ 任务基准域名: {base_host}")
    print(f"  ├─ 任务 RID: {rid}")

    # 步骤 2: 请求 dudu 接口校验任务并获取微信真实文章地址
    now_ts = int(time.time() * 1000)
    dudu_url = f"{base_host}/xiaoxinxin/dudu?rid={rid}&time={now_ts}&psgn=168&vs=1003"
    
    try:
        res_dudu = session.get(dudu_url, headers=headers, timeout=10).json()
    except Exception as e:
        print(f"❌ [步骤2] 请求 dudu 接口异常: {e}")
        return False, 0, f"dudu接口网络异常: {e}"

    if res_dudu.get("errcode") != 0:
        msg = res_dudu.get("msg", "dudu验证失败")
        print(f"⚠️ [步骤2] dudu 接口返回非0: {msg}")
        return False, 0, msg

    article_link = res_dudu.get("data", {}).get("link", "")
    print(f"  ├─ 成功获取文章链接: {article_link[:60]}...")

    # 步骤 3: 打开微信文章并模拟 30 - 60 秒的阅读停留与滑动模拟
    read_seconds = round(random.uniform(READ_DURATION_MIN, READ_DURATION_MAX), 1)
    print(f"  ├─ 开始模拟真实阅读 (预计停留并滚动 {read_seconds} 秒)...")
    
    try:
        session.get(article_link, headers=headers, timeout=10)
    except Exception as e:
        print(f"  │  ⚠️ 访问文章链接网络波动 (继续计时): {e}")

    # 模拟在文章页中的滑动与阅读间隔
    step_sleep = 5
    elapsed = 0
    while elapsed < read_seconds:
        sleep_chunk = min(step_sleep, read_seconds - elapsed)
        time.sleep(sleep_chunk)
        elapsed += sleep_chunk
        print(f"  │  ...已阅读模拟滑动中 [{elapsed:.0f}/{read_seconds:.0f} 秒]")

    # 步骤 4: 请求 jinright 接口提交阅读时长并结算金币
    now_ts = int(time.time() * 1000)
    read_duration_int = int(read_seconds)
    jinright_url = f"{base_host}/xiaoxinxin/jinright?rid={rid}&time={read_duration_int}&timestamp={now_ts}"

    try:
        res_jinright = session.get(jinright_url, headers=headers, timeout=10).json()
    except Exception as e:
        print(f"❌ [步骤4] 结算金币网络异常: {e}")
        return False, 0, f"结算接口网络异常: {e}"

    if res_jinright.get("errcode") == 0:
        data = res_jinright.get("data", {})
        earned_gold = int(data.get("gold", 0))
        day_read = data.get("day_read", 0)
        day_gold = data.get("day_gold", 0)
        last_gold = data.get("last_gold", 0)

        if earned_gold > 0:
            print(f"  └─ ✅ [加币验证成功] 本篇获得: +{earned_gold} 金币！今日已读: {day_read} 篇, 今日累计金币: {day_gold}, 余额账户: {last_gold}")
            return True, earned_gold, "成功"
        else:
            print(f"  └─ ⚠️ [提示] 结算成功但增加金币为 0（可能是重复阅读或受限），响应: {data}")
            return True, 0, "金币为0"
    else:
        msg = res_jinright.get("msg", "结算错误")
        print(f"  └─ ❌ [结算失败] 原因: {msg}")
        return False, 0, msg

def run_account(account, host_domain, max_read):
    """运行单个账号流程（包含连续报错容错机制）"""
    idx = account["index"]
    unionid = account["unionid"]
    cookie_str = account["cookie"]
    
    print(f"\n==================================================")
    print(f"🚀 正在运行 [账号{idx}] (UnionID: {unionid[:6]}***{unionid[-4:] if len(unionid)>10 else ''})")
    print(f"==================================================")
    
    headers = get_headers(cookie_str)
    session = requests.Session()
    
    # 查初始收益
    status_before = get_user_status(session, host_domain, unionid, headers)
    if status_before and status_before.get("errcode") == 0:
        b_data = status_before.get("data", {})
        print(f"📊 初始状态: 今日已读 {b_data.get('day_read', 0)} 篇, 今日金币: {b_data.get('day_gold', 0)}, 账户余额: {b_data.get('last_gold', 0)}")
    else:
        print("📊 初始状态: 获取异常或数据为空")
    
    total_earned_gold = 0
    success_reads = 0
    continuous_error_count = 0
    
    read_idx = 1
    while success_reads < max_read:
        success, gold, err_msg = process_single_read(session, host_domain, headers, unionid, read_idx, max_read)
        
        if success:
            success_reads += 1
            total_earned_gold += gold
            continuous_error_count = 0  # 成功一次后重置连续错误计数器
            read_idx += 1
        else:
            continuous_error_count += 1
            print(f"⚠️ [容错机制] 当前连续报错/失败次数: [{continuous_error_count}/{MAX_CONTINUOUS_ERRORS}]，原因: {err_msg}")
            
            if continuous_error_count >= MAX_CONTINUOUS_ERRORS:
                print(f"❌ [账号终止] 连续报错已达 {MAX_CONTINUOUS_ERRORS} 次，停止运行当前账号。")
                break
                
            retry_wait = 8
            print(f"⏳ 等待 {retry_wait} 秒后重试...")
            time.sleep(retry_wait)
            continue
            
        if success_reads < max_read:
            interval = round(random.uniform(3.0, 5.0), 1)
            print(f"⏳ 间隔等待 {interval} 秒后继续下一篇...")
            time.sleep(interval)

    # 查运行后总结
    status_after = get_user_status(session, host_domain, unionid, headers)
    gold_msg = ""
    if status_after and status_after.get("errcode") == 0:
        a_data = status_after.get("data", {})
        gold_msg = f"今日已读 {a_data.get('day_read', 0)} 篇, 今日金币: {a_data.get('day_gold', 0)}, 账户余额: {a_data.get('last_gold', 0)}"
        print(f"\n🎉 [账号{idx}] 运行总结:")
        print(f"  ├─ 本次完成阅读: {success_reads} 篇")
        print(f"  ├─ 本次新增金币: +{total_earned_gold} 金币")
        print(f"  └─ 最新账号概览: {gold_msg}")

    summary = f"账号 [{idx}] 完成阅读 {success_reads} 篇，新增 +{total_earned_gold} 金币。最新状态: {gold_msg}"
    return summary

def main():
    print("==================================================")
    print("      小阅阅全自动阅读脚本 ")
    print("==================================================")
    host_domain = os.getenv("xyy_domain", "").strip()
    if not host_domain or not (host_domain.startswith("http://") or host_domain.startswith("https://")):
        host_domain = DEFAULT_DOMAIN
    host_domain = host_domain.rstrip("/")
    try:
        max_read = int(os.getenv("xyy_max_read", DEFAULT_MAX_READ))
    except ValueError:
        max_read = DEFAULT_MAX_READ
        
    accounts = get_accounts()
    if not accounts:
        sys.exit(1)
        
    print(f"ℹ️ 共检测到 {len(accounts)} 个账号配置 | 单账号目标篇数: {max_read} 篇 | 单篇阅读时长: {READ_DURATION_MIN}-{READ_DURATION_MAX} 秒\n")
    
    results = []
    for account in accounts:
        res_text = run_account(account, host_domain, max_read)
        results.append(res_text)
        time.sleep(2)
        
    final_summary = "\n".join(results)
    print("\n==================================================")
    print("🎉 所有账号处理完毕！")
    print("==================================================")
    print(final_summary)
    
    # 发送青龙通知
    send("小阅阅全自动阅读任务报告", final_summary)

if __name__ == "__main__":
    main()

