#微信扫描二维码抓包要authorization请求头删除Bearer 
#示例eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOjIxMzIsIm9wZW5pZCI6Im81MURzNjZkLVhnUkdRNXZlWjUtYjhZaF9sUm8iLCJpYXQiO535
#环境变量名称xi多账号#号隔开自动提现后，需上小程序自己手动收款
#小程序://商联道/CaVyhu35qsFFvMz
#小程序://商联道/CaVyhu35qsFFvMz
#小程序://商联道/CaVyhu35qsFFvMz
import requests
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 核心配置项 ====================
ENV_NAME = "xi"          # 环境变量名称（多账号Token用 # 分隔）
SPLIT_CHAR = "#"         # 多账号分隔符

# 广告配置
AD_WATCH_SEC = 33
AD_LOOP_SLEEP = 15

# 阅读间隔配置
ARTICLE_NORMAL_MIN = 15
ARTICLE_NORMAL_MAX = 20
ARTICLE_FINISHED_MIN = 3
ARTICLE_FINISHED_MAX = 5

# 阅读范围与模式
ARTICLE_START_ID = 38
ARTICLE_END_ID = 1
ARTICLE_WATCH_SEC = 33
ARTICLE_REVERSE = True

# 并发&网络配置
MAX_WORKERS = 10
REQ_TIMEOUT = 15
# =====================================================

# 通用请求头
def get_headers(token):
    return {
        "Host": "mini.shangliandao.cn",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254193e) XWEB/19841",
        "xweb_xhr": "1",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Referer": "https://servicewechat.com/wx31a4573b0bf1fcb3/27/page-frame.html",
    }

# 【新增】每日签到函数
def do_sign_in(token, idx):
    headers = get_headers(token)
    sign_url = "https://mini.shangliandao.cn/api/rewards/sign-in"
    try:
        resp = requests.post(sign_url, json={}, headers=headers, timeout=REQ_TIMEOUT)
        res = resp.json()
        if res.get("status") == 200:
            bean = res["data"].get("golden_beans", 0)
            streak = res["data"].get("consecutive_days", 0)
            print(f"【账号{idx}】✅ 签到成功 | 获得金豆:{bean} | 连续签到:{streak}天")
        else:
            print(f"【账号{idx}】ℹ️ {res.get('msg','签到失败')}")
    except Exception as e:
        print(f"【账号{idx}】❌ 签到异常：{str(e)}")

# 获取账号基础状态（金豆、广告剩余次数）
def get_account_status(token, idx):
    headers = get_headers(token)
    try:
        resp = requests.get(
            "https://mini.shangliandao.cn/api/rewards/home-reward-status",
            headers=headers,
            timeout=REQ_TIMEOUT
        )
        if resp.status_code == 401:
            print(f"【账号{idx}】❌ Token已过期")
            return "EXPIRED", None
        if resp.status_code != 200:
            print(f"【账号{idx}】❌ 状态接口异常")
            return "FAIL", None
        res = resp.json()
        return "OK", res
    except Exception as e:
        print(f"【账号{idx}】❌ 网络异常：{str(e)}")
        return "NET_ERR", None

# 获取当前账户金豆数量
def get_bean(token, idx):
    code, data = get_account_status(token, idx)
    if code == "OK":
        return float(data["data"].get("golden_bean_balance", 0.00))
    return 0.00

# ===================== 答题模块 =====================
def auto_answer(quiz):
    if not quiz or "question" not in quiz or "options" not in quiz or len(quiz["options"]) == 0:
        return quiz["options"][0]["id"]

    question = quiz["question"].strip().lower()
    options = quiz["options"]

    reverse_keywords = [
        "不", "错", "错误", "不当", "不正确", "有误", "禁止", "避免",
        "不能", "不要", "不该", "不符", "不属于", "错误的是", "不正确的是",
        "切勿", "严禁", "不可", "错误做法", "不利", "危害", "坏处", "无",
        "非", "否", "不准", "不许", "不宜", "不对", "不行", "不可以"
    ]
    is_reverse = any(k in question for k in reverse_keywords)

    absolute_correct = [
        "及时就医", "立即就诊", "咨询医生", "听从医嘱", "按时服药", "正规医院",
        "对症治疗", "专业指导", "遵医嘱", "定期检查", "接种疫苗", "预防为主",
        "规律作息", "早睡早起", "劳逸结合", "心态平和", "情绪稳定", "卧床休息",
        "静养", "保证睡眠", "充足睡眠", "开窗通风", "保持通风", "注意保暖",
        "清淡饮食", "低盐少油", "低糖低脂", "七分饱", "合理膳食", "均衡营养",
        "多喝温水", "多喝水", "细嚼慢咽", "三餐规律", "搭配蔬菜", "搭配粗粮",
        "适度运动", "循序渐进", "量力而行", "散步", "慢跑", "低强度运动",
        "加强锻炼", "饭后散步", "热身运动", "勤洗手", "注意卫生", "科学防护",
        "佩戴口罩", "远离危险", "安全第一", "减少主食", "控制主食", "代替主食",
        "适量食用", "当主食吃", "趁热吃"
    ]

    normal_correct = [
        "休息", "放松", "按时", "准时", "保暖", "防寒", "防暑", "适量", "适度",
        "少量", "慢慢", "走路", "耐心", "陪伴", "缓解疲劳", "安全", "戒烟限酒",
        "搭配食用", "减少食用", "清淡", "温热", "熟食", "洗净", "通风", "保湿"
    ]

    normal_wrong = [
        "晚睡", "不吃早餐", "久坐", "憋尿", "挑食", "暴晒", "情绪激动", "生气",
        "争吵", "冷饮", "空腹", "拖延", "乱吃", "用力过猛", "挤压", "饭后吃",
        "多吃", "额外吃", "代替正餐", "大量食用", "生冷", "辛辣", "油腻"
    ]

    absolute_wrong = [
        "熬夜", "通宵", "睡眠不足", "暴饮暴食", "喝冰水", "生冷食物", "辛辣刺激",
        "过量进食", "酗酒", "饮酒", "喝酒", "吸烟", "抽烟", "自行用药", "乱用药",
        "过量服药", "硬扛", "硬撑", "不治", "剧烈运动", "高强度运动", "强行坚持",
        "酒后运动", "带病运动", "空腹吃", "过量吃", "饭后多吃", "多吃两个",
        "空腹食用", "大量吃"
    ]

    zongzi_good = ["当主食", "减少米饭", "搭配蔬菜", "适量食用", "趁热吃", "搭配茶水"]
    zongzi_bad = ["空腹吃", "饭后吃", "多吃两个", "多吃几个", "大量吃", "代替所有主食"]
    health_good = ["温热饮食", "少食多餐", "细嚼慢咽"]
    health_bad = ["空腹进食", "暴饮暴食", "生冷刺激"]
    safe_good = ["及时报警", "紧急疏散", "切断电源"]
    safe_bad = ["乘坐电梯", "贪恋财物", "盲目逃生"]

    score_list = []
    for opt in options:
        opt_text = opt["text"].strip().lower()
        score = 0

        for word in absolute_correct:
            if word in opt_text:
                score += 25
        for word in normal_correct:
            if word in opt_text:
                score += 15
        for word in normal_wrong:
            if word in opt_text:
                score -= 20
        for word in absolute_wrong:
            if word in opt_text:
                score -= 30

        if "粽子" in question or "端午" in question:
            for word in zongzi_good: score += 30
            for word in zongzi_bad: score -= 40
        if "肠胃" in question or "养生" in question:
            for word in health_good: score += 25
            for word in health_bad: score -= 35
        if "消防" in question or "安全" in question:
            for word in safe_good: score += 25
            for word in safe_bad: score -= 35

        score_list.append({"id": opt["id"], "text": opt["text"], "score": score})

    if is_reverse:
        score_list.sort(key=lambda x: x["score"])
    else:
        score_list.sort(key=lambda x: x["score"], reverse=True)

    best = score_list[0]
    if len(score_list) >= 2 and best["score"] == score_list[1]["score"]:
        for fid in ["B", "A", "C", "D"]:
            for item in score_list:
                if item["id"] == fid:
                    best = item
                    break
            break
    return best["id"]

# 广告任务逻辑
def report_ad(headers, idx, i, total, current_bean, total_earn):
    try:
        requests.get("https://mini.shangliandao.cn/api/rewards/home-reward-config", headers=headers, timeout=REQ_TIMEOUT)
        print(f"【账号{idx}】🎬 广告 {i}/{total} 开始观看，时长 {AD_WATCH_SEC} 秒")
        time.sleep(AD_WATCH_SEC)

        post_data = {"scene": "home_reward", "watch_seconds": AD_WATCH_SEC, "session_id": f"ad_{i}"}
        resp = requests.post(
            "https://mini.shangliandao.cn/api/rewards/ad-complete",
            json=post_data,
            headers=headers,
            timeout=REQ_TIMEOUT
        )
        res = resp.json()
        add_bean = float(res["data"].get("amount", 0.00)) if res.get("status") == 200 else 0.00
        new_current = current_bean + add_bean
        new_total = total_earn + add_bean

        print(f"【账号{idx}】🎬 广告 {i}/{total} 观看完成 ✅")
        print(f"【账号{idx}】💎 本次获得金豆：{add_bean:.2f} | 累计获得：{new_total:.2f} | 当前账户金豆：{new_current:.2f}")
        return add_bean, new_total, new_current
    except Exception as e:
        print(f"【账号{idx}】🎬 广告 {i}/{total} ❌ 异常：{str(e)}")
        return 0.00, total_earn, current_bean

# 单篇文章阅读 + 答题 + 翻倍广告
def run_article(art_id, token, idx, total_earn, current_bean):
    headers = get_headers(token)
    print(f"\n【账号{idx}】📖 开始阅读文章 {art_id}")
    try:
        res = requests.get(f"https://mini.shangliandao.cn/api/article/{art_id}", headers=headers, timeout=REQ_TIMEOUT).json()
        if res.get("status") != 200:
            print(f"【账号{idx}】📖 文章 {art_id} 接口异常")
            return total_earn, current_bean, True

        art_data = res["data"]
        is_finished = art_data["today_status"]["completed_today"]
        if is_finished:
            print(f"【账号{idx}】📖 文章 {art_id} 今日已完成")
            return total_earn, current_bean, is_finished

        read_sec = art_data.get("read_duration", 10)
        print(f"【账号{idx}】📖 文章 {art_id} 阅读时长 {read_sec} 秒")
        time.sleep(read_sec)

        ans_id = auto_answer(art_data["quiz"])
        quiz_res = requests.post(
            f"https://mini.shangliandao.cn/api/article/{art_id}/quiz",
            json={"answer": ans_id, "read_seconds": read_sec},
            headers=headers
        ).json()

        base_bean = 0.00
        if quiz_res.get("status") == 200:
            correct = quiz_res["data"].get("quiz_correct")
            base_bean = float(quiz_res["data"].get("bean_amount", 0.00))
            status = "✅ 答题正确" if correct else "❌ 答题错误"
            print(f"【账号{idx}】📖 文章 {art_id} {status}")

        total_earn += base_bean
        current_bean += base_bean
        print(f"【账号{idx}】💎 基础奖励：{base_bean:.2f} | 累计获得：{total_earn:.2f} | 当前账户金豆：{current_bean:.2f}")

        if art_data.get("double_bean_video"):
            print(f"【账号{idx}】📖 文章 {art_id} 触发翻倍广告，观看 {ARTICLE_WATCH_SEC} 秒")
            time.sleep(ARTICLE_WATCH_SEC)
            ad_data = {"scene": "article_reward_double", "watch_seconds": ARTICLE_WATCH_SEC, "session_id": str(art_id)}
            requests.post("https://mini.shangliandao.cn/api/rewards/ad-complete", json=ad_data, headers=headers)
            time.sleep(1)

            double_res = requests.post(f"https://mini.shangliandao.cn/api/article/{art_id}/double-reward", headers=headers).json()
            if double_res.get("status") == 200:
                double_total = float(double_res["data"].get("total_beans", 0.00))
                double_bean = double_total - base_bean
                total_earn += double_bean
                current_bean += double_bean
                print(f"【账号{idx}】📖 文章 {art_id} 翻倍成功")
                print(f"【账号{idx}】💎 翻倍奖励：{double_bean:.2f} | 累计获得：{total_earn:.2f} | 当前账户金豆：{current_bean:.2f}")
        return total_earn, current_bean, is_finished
    except Exception as e:
        print(f"【账号{idx}】📖 文章 {art_id} 异常：{str(e)}")
        return total_earn, current_bean, True

# 自动检测提现（无开关，全自动）
def auto_withdraw_check(token, idx):
    headers = get_headers(token)
    print(f"\n【账号{idx}】======== 自动检测提现状态 ========")
    status_url = "https://mini.shangliandao.cn/api/user/golden-bean/withdraw/status"
    try:
        status_resp = requests.get(status_url, headers=headers, timeout=REQ_TIMEOUT).json()
    except:
        print(f"【账号{idx}】❌ 网络异常，查询提现状态失败，跳过提现")
        return

    if status_resp.get("status") != 200:
        print(f"【账号{idx}】❌ 提现状态接口异常，跳过提现")
        return

    data = status_resp.get("data", {})
    withdrawn_today = data.get("withdrawn_today", False)
    can_withdraw = data.get("can_withdraw", False)
    bean_balance = float(data.get("golden_bean_balance", 0))
    min_yuan = float(data.get("withdraw_min_yuan", 0))

    print(f"【账号{idx}】ℹ️ 当前金豆：{bean_balance:.2f} | 最低提现门槛：{min_yuan}元")
    print(f"【账号{idx}】ℹ️ 今日已提现：{withdrawn_today} | 满足提现条件：{can_withdraw}")

    if withdrawn_today:
        print(f"【账号{idx}】ℹ️ 今日已完成提现，自动跳过")
        return
    if not can_withdraw:
        print(f"【账号{idx}】ℹ️ 账户余额未达到提现门槛，自动跳过")
        return

    print(f"【账号{idx}】✅ 检测符合提现条件，开始执行提现")
    apply_url = "https://mini.shangliandao.cn/api/user/golden-bean/withdraw/apply"
    try:
        apply_resp = requests.post(apply_url, json={}, headers=headers, timeout=REQ_TIMEOUT).json()
    except:
        print(f"【账号{idx}】❌ 发起提现申请失败，终止提现")
        return

    if apply_resp.get("status") != 200 or "biz_no" not in apply_resp.get("data", {}):
        print(f"【账号{idx}】❌ 无法生成提现单号，提现失败")
        return

    biz_no = apply_resp["data"]["biz_no"]
    print(f"【账号{idx}】✅ 已生成提现单号：{biz_no}")

    confirm_url = "https://mini.shangliandao.cn/api/user/golden-bean/withdraw/reconfirm"
    confirm_data = {"biz_no": biz_no}
    try:
        requests.post(confirm_url, json=confirm_data, headers=headers, timeout=REQ_TIMEOUT)
    except:
        print(f"【账号{idx}】❌ 提现二次确认请求异常")
        return

    print(f"【账号{idx}】✅ 提现提交完成，请上小程序确定收款")

# 单账号完整流程：签到 → 广告 → 阅读 → 自动提现
def account_task(token, idx):
    print(f"\n=============================================")
    print(f"============= 【账号 {idx}】 启动任务 =============")
    print(f"=============================================")

    # 第一步：执行签到
    do_sign_in(token, idx)
    time.sleep(2)

    code, status_data = get_account_status(token, idx)
    if code != "OK":
        return f"【账号{idx}】任务失败"

    init_bean = get_bean(token, idx)
    current_bean = init_bean
    total_earn = 0.00
    ad_remain = status_data["data"].get("ad_remaining_today", 0)
    headers = get_headers(token)

    print(f"【账号{idx}】💰 初始账户金豆：{init_bean:.2f} | 今日剩余广告：{ad_remain}次")

    # 广告任务
    print(f"\n【账号{idx}】======== 开始执行广告任务 ========")
    if ad_remain <= 0:
        print(f"【账号{idx}】✅ 今日广告已全部完成")
    else:
        for i in range(1, ad_remain + 1):
            add, total_earn, current_bean = report_ad(headers, idx, i, ad_remain, current_bean, total_earn)
            if i < ad_remain:
                print(f"【账号{idx}】⏸️ 广告轮次间隔，等待 {AD_LOOP_SLEEP} 秒")
                time.sleep(AD_LOOP_SLEEP)
    print(f"【账号{idx}】🎉 广告阶段累计收益：{total_earn:.2f}")

    # 阅读任务
    print(f"\n【账号{idx}】======== 开始执行阅读任务 ========")
    if ARTICLE_REVERSE:
        art_id_list = range(ARTICLE_START_ID, ARTICLE_END_ID - 1, -1)
        print(f"【账号{idx}】📚 阅读范围：ID {ARTICLE_START_ID} ~ {ARTICLE_END_ID}（倒序读取）")
        print(f"【账号{idx}】⏱️ 正常文章随机间隔 {ARTICLE_NORMAL_MIN}~{ARTICLE_NORMAL_MAX} 秒 | 已完成文章随机间隔 {ARTICLE_FINISHED_MIN}~{ARTICLE_FINISHED_MAX} 秒")
    else:
        art_id_list = range(ARTICLE_START_ID, ARTICLE_END_ID + 1)
        print(f"【账号{idx}】📚 阅读范围：ID {ARTICLE_START_ID} ~ {ARTICLE_END_ID}（正序读取）")

    art_list = list(art_id_list)
    for index, aid in enumerate(art_list):
        total_earn, current_bean, is_finished = run_article(aid, token, idx, total_earn, current_bean)
        if index >= len(art_list) - 1:
            continue
        if is_finished:
            sleep_sec = random.randint(ARTICLE_FINISHED_MIN, ARTICLE_FINISHED_MAX)
            print(f"【账号{idx}】⏸️ 已完成文章间隔，等待 {sleep_sec} 秒")
        else:
            sleep_sec = random.randint(ARTICLE_NORMAL_MIN, ARTICLE_NORMAL_MAX)
            print(f"【账号{idx}】⏸️ 正常文章间隔，等待 {sleep_sec} 秒")
        time.sleep(sleep_sec)

    # 全部任务结束 → 自动检测提现
    auto_withdraw_check(token, idx)

    # 账号汇总
    print(f"\n【账号{idx}】============ 账号任务汇总 ============")
    print(f"【账号{idx}】💰 初始金豆：{init_bean:.2f}")
    print(f"【账号{idx}】💰 最终金豆：{current_bean:.2f}")
    print(f"【账号{idx}】📈 本次总计收益：{total_earn:.2f}")
    return f"【账号{idx}】全部任务执行完成"

# 程序入口
def main():
    print("=" * 60)
    print("🚀 商联道全自动脚本 | 签到+广告+阅读+自动提现")
    print("=" * 60)

    env_val = os.environ.get(ENV_NAME, "")
    if not env_val:
        print(f"❌ 未配置环境变量 {ENV_NAME}")
        return
    token_list = [t.strip() for t in env_val.split(SPLIT_CHAR) if t.strip()]
    if not token_list:
        print("❌ 无有效账号")
        return

    print(f"✅ 共加载 {len(token_list)} 个账号，开始并发执行")
    print(f"✅ 广告时长：{AD_WATCH_SEC}秒 | 广告间隔：{AD_LOOP_SLEEP}秒\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for idx, token in enumerate(token_list, 1):
            futures.append(executor.submit(account_task, token, idx))
        for future in as_completed(futures):
            try:
                print(f"\n" + future.result())
            except Exception as e:
                print(f"❌ 线程异常：{str(e)}")

    print("\n" + "=" * 60)
    print("🏁 所有账号任务全部执行完毕")
    print("=" * 60)

if __name__ == "__main__":
    main()