import os
import configparser
from quark import QuarkTransfer

CONFIG_PATH = "config.ini"

def save_cookie_to_config(cookie_str):
    cfg = configparser.ConfigParser()
    cfg["quark"] = {"cookie": cookie_str}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)
    print("\n====================【提示】====================")
    print("✅ Cookie 已保存至本地配置文件，下次运行无需重复输入！")
    print("================================================\n")

def get_saved_cookie():
    if not os.path.exists(CONFIG_PATH):
        return None
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")
    if "quark" in cfg and "cookie" in cfg["quark"]:
        return cfg["quark"]["cookie"].strip()
    return None

def input_cookie_flow():
    print("====================【Cookie设置弹窗】====================")
    print("请粘贴浏览器获取的完整夸克网盘Cookie：")
    new_cookie = input("Cookie > ").strip()
    if len(new_cookie) < 10:
        print("\n❌ Cookie长度过短，输入无效！")
        return None
    save_cookie_to_config(new_cookie)
    return new_cookie

def transfer_flow(cookie):
    print("\n====================【转存链接输入弹窗】====================")
    share_url = input("请输入夸克分享链接 > ").strip()
    if not share_url.startswith("https://pan.quark.cn/s/"):
        print("\n❌ 链接格式错误！必须是 pan.quark.cn/s/ 开头分享链接")
        return

    print("\n⏳ 正在执行转存，请稍候...")
    tool = QuarkTransfer(cookie)
    res = tool.transfer_store(share_url)

    if res == "url_err":
        print("\n❌ 失败：无法解析分享链接ID，链接失效")
    elif res == "cookie_err":
        print("\n❌ 失败：Cookie失效/错误，请重新设置Cookie！")
    elif res == "detail_err":
        print("\n❌ 失败：无法读取分享文件信息")
    elif res == "skip":
        print("\nℹ️ 提示：该文件已转存过，数据库存在记录，跳过操作")
    elif res == "task_fail":
        print("\n❌ 失败：网盘转存任务执行超时")
    elif res.startswith("success|"):
        _, fname, new_link = res.split("|")
        print("\n====================【转存成功】====================")
        print(f"文件名称：{fname}")
        print(f"新分享链接：{new_link}")
        print("====================================================")
    else:
        print("\n❌ 未知错误，转存失败")

def main():
    print("===== 夸克网盘交互式自动转存工具（青龙面板专用）=====\n")
    # 读取本地保存Cookie
    cookie = get_saved_cookie()
    if not cookie:
        cookie = input_cookie_flow()
        if not cookie:
            print("Cookie无效，程序退出")
            return
    else:
        print(f"ℹ️ 检测到已保存Cookie，是否重新输入？(y/n)")
        op = input("输入选择 > ").strip().lower()
        if op == "y":
            cookie = input_cookie_flow()
            if not cookie:
                print("Cookie无效，程序退出")
                return

    # 循环转存
    while True:
        transfer_flow(cookie)
        print("\n是否继续转存其他链接？(y/n)")
        cont = input("选择 > ").strip().lower()
        if cont != "y":
            print("程序结束，再见！")
            break

if __name__ == "__main__":
    main()