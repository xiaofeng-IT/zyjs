import requests
import re
import time
import random
import logging

logging.getLogger().setLevel(logging.INFO)

def get_id_from_url(url) -> str:
    pattern = r"/s/(\w+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ""

def generate_timestamp(length):
    timestamps = str(time.time() * 1000)
    return int(timestamps[0:length])

class QuarkTransfer:
    ad_pwd_id = "5d84a8e575d6"

    def __init__(self, cookie: str) -> None:
        self.headers = {
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'sec-ch-ua-mobile': '?0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'origin': 'https://pan.quark.cn',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pan.quark.cn/',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': cookie
        }

    def transfer_store(self, share_url: str):
        pwd_id = get_id_from_url(share_url)
        if not pwd_id:
            logging.error(f"链接解析失败: {share_url}")
            return None

        stoken = self.get_stoken(pwd_id)
        if not stoken:
            logging.error(f"获取stoken失败，Cookie失效或链接过期: {share_url}")
            return None

        detail = self.detail(pwd_id, stoken)
        file_name = detail.get('title')
        if not file_name:
            logging.error("无法读取文件名")
            return None

        from sqlite import fetch_files
        if not fetch_files(file_name):
            logging.info(f"【跳过】文件已存在库中：{file_name}")
            return "skip"

        first_id = detail.get("fid")
        share_fid_token = detail.get("share_fid_token")
        file_type = detail.get("file_type")

        save_task = self.save_task_id(pwd_id, stoken, first_id, share_fid_token)
        task_result = self.task(save_task)
        if not task_result:
            logging.error(f"转存任务失败 {file_name}")
            return None

        file_id = task_result.get("data").get("save_as").get("save_as_top_fids")[0]

        if not file_type:
            dir_file_list = self.get_dir_file(file_id)
            self.del_ad_file(dir_file_list)
            self.add_custom_ad(file_id)

        share_task = self.share_task_id(file_id, file_name)
        share_data = self.task(share_task)
        share_id = share_data.get("data").get("share_id")
        new_share_link = self.get_share_link(share_id)

        from sqlite import insert_files
        insert_files(file_id, file_name, file_type, new_share_link)
        logging.info(f"✅转存完成 | 文件:{file_name} | 新链接:{new_share_link}")
        return new_share_link

    def get_stoken(self, pwd_id: str):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc&uc_param_str=&__dt=405&__t={generate_timestamp(13)}"
        payload = {"pwd_id": pwd_id, "passcode": ""}
        resp = requests.post(url, json=payload, headers=self.headers).json()
        if resp.get("data"):
            return resp["data"]["stoken"]
        return ""

    def detail(self, pwd_id, stoken):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
        params = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": 0,
            "_page": 1,
            "_size": "50",
        }
        resp = requests.get(url=url, headers=self.headers, params=params).json()
        list_info = resp.get("data").get("list")[0]
        data = {
            "title": list_info.get("file_name"),
            "file_type": list_info.get("file_type"),
            "fid": list_info.get("fid"),
            "pdir_fid": list_info.get("pdir_fid"),
            "share_fid_token": list_info.get("share_fid_token")
        }
        return data

    def save_task_id(self, pwd_id, stoken, first_id, share_fid_token, to_pdir_fid=0):
        logging.info("发起转存任务...")
        url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": generate_timestamp(13),
        }
        data = {
            "fid_list": [first_id],
            "fid_token_list": [share_fid_token],
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link"
        }
        resp = requests.post(url, json=data, headers=self.headers, params=params)
        task_id = resp.json().get('data').get('task_id')
        return task_id

    def task(self, task_id, trice=10):
        logging.info("等待网盘任务完成...")
        for i in range(trice):
            url = f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}&retry_index={i}&__dt=21192&__t={generate_timestamp(13)}"
            resp = requests.get(url, headers=self.headers).json()
            if resp.get('data').get('status') == 2:
                return resp
            time.sleep(0.8)
        logging.warning("任务等待超时")
        return False

    def share_task_id(self, file_id, file_name):
        url = "https://drive-pc.quark.cn/1/clouddrive/share?pr=ucpro&fr=pc&uc_param_str="
        data = {
            "fid_list": [file_id],
            "title": file_name,
            "url_type": 1,
            "expired_type": 1
        }
        resp = requests.post(url=url, json=data, headers=self.headers)
        return resp.json().get("data").get("task_id")

    def get_share_link(self, share_id):
        url = "https://drive-pc.quark.cn/1/clouddrive/share/password?pr=ucpro&fr=pc&uc_param_str="
        data = {"share_id": share_id}
        resp = requests.post(url=url, json=data, headers=self.headers)
        return resp.json().get("data").get("share_url")

    def get_dir_file(self, dir_id) -> list:
        logging.info(f"遍历文件夹ID：{dir_id}")
        url = f"https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str=&pdir_fid={dir_id}&_page=1&_size=50&_fetch_total=1&_fetch_sub_dirs=0&_sort=updated_at:desc"
        resp = requests.get(url=url, headers=self.headers)
        return resp.json().get('data').get('list')

    def del_file(self, file_id):
        logging.info(f"删除广告文件ID：{file_id}")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/delete?pr=ucpro&fr=pc&uc_param_str="
        data = {"action_type": 2, "filelist": [file_id], "exclude_fids": []}
        resp = requests.post(url=url, json=data, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("data").get("task_id")
        return False

    def del_ad_file(self, file_list):
        from ad_check import ad_check
        for folder in file_list:
            file_items = folder.get("files", [])
            for file in file_items:
                file_name = file.get("file_name")
                if ad_check(file_name):
                    task_id = self.del_file(file.get("fid"))
                    if task_id:
                        self.task(task_id, 3)

    def add_custom_ad(self, target_dir_id):
        logging.info("植入自定义附加文件...")
        pwd_id = self.ad_pwd_id
        stoken = self.get_stoken(pwd_id)
        if not stoken:
            logging.error("自定义广告资源链接失效，跳过植入")
            return
        detail = self.detail(pwd_id, stoken)
        ad_fid = detail.get("fid")
        ad_token = detail.get("share_fid_token")
        task_id = self.save_task_id(pwd_id, stoken, ad_fid, ad_token, target_dir_id)
        self.task(task_id, 1)
        logging.info("自定义文件植入完成")

    def search_file(self, file_name):
        logging.info(f"网盘搜索：{file_name}")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/search?pr=ucpro&fr=pc&uc_param_str=&_page=1&_size=50&_fetch_total=1&_sort=file_type:desc,updated_at:desc&_is_hl=1"
        params = {"q": file_name}
        resp = requests.get(url=url, headers=self.headers, params=params)
        return resp.json().get('data').get('list')