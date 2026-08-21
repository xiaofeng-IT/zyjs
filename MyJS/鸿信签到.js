/*
名称：hxzm 自动签到 JS版
环境变量：hxzm
格式：账号#密码
多账号：换行分隔
功能：随机UA + 登录 + 签到 + 查询余额
*/

const axios = require('axios');

// 随机UA池
const UA_LIST = [
  "Mozilla/5.0 (Linux; Android 11; V1824A Build/RP1A.200720.012; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/83.0.4103.106 Mobile Safari/537.36 uni-app Html5Plus/1.0",
  "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
  "Mozilla/5.0 (Linux; Android 13; MI 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
  "Mozilla/5.0 (Linux; Android 10; Redmi K40) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
  "Mozilla/5.0 (Linux; Android 11; ONEPLUS A9000) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36"
];

// 读取环境变量
const hxzm = process.env.hxzm || "";
if (!hxzm) {
  console.log("❌ 请添加环境变量 hxzm");
  process.exit(1);
}

// 基础配置
const BASE_URL = "https://im.lsbkym.cn";

// 随机UA
function getRandomUA() {
  return UA_LIST[Math.floor(Math.random() * UA_LIST.length)];
}

// 登录
async function login(account, pwd) {
  try {
    const headers = {
      "User-Agent": getRandomUA(),
      "Content-Type": "application/json"
    };
    const data = {
      account: account,
      password: pwd,
      code: "",
      client_id: "",
      rememberMe: false,
      lang: "zh"
    };
    const res = await axios.post(`${BASE_URL}/common/Pub/login`, data, { headers });
    if (res.data.code === 0) {
      console.log("✅ 登录成功");
      return res.data.data.authToken;
    } else {
      console.log("❌ 登录失败：" + res.data.msg);
      return null;
    }
  } catch (e) {
    console.log("❌ 登录异常");
    return null;
  }
}

// 签到
async function signIn(token) {
  try {
    const headers = {
      "User-Agent": getRandomUA(),
      "Authorization": token,
      "Content-Type": "application/json"
    };
    const res = await axios.post(`${BASE_URL}/enterprise/im/signIn`, {}, { headers });
    if (res.data.code === 0) {
      const reward = res.data.data.reward || 0;
      const streak = res.data.data.streak || 0;
      return `✅ 签到成功 | 奖励${reward}元 | 连续${streak}天`;
    } else {
      return `❌ 签到失败：${res.data.msg}`;
    }
  } catch (e) {
    return "❌ 签到异常";
  }
}

// 查询余额
async function getBalance(token) {
  try {
    const headers = {
      "User-Agent": getRandomUA(),
      "Authorization": token,
      "Content-Type": "application/json"
    };
    const data = { type: 0, page: 1 };
    const res = await axios.post(`${BASE_URL}/enterprise/im/getBillList`, data, { headers });
    if (res.data.code === 0) {
      const balance = res.data.data.balance || "0.00";
      return `💰 余额：${balance} 元`;
    }
  } catch (e) {}
  return "❌ 查询余额失败";
}

// 执行多账号
(async () => {
  const users = hxzm.trim().split("\n").filter(u => u.trim());
  for (let i = 0; i < users.length; i++) {
    const line = users[i].trim();
    if (!line.includes("#")) continue;
    const [account, pwd] = line.split("#", 2);
    console.log(`\n========== 账号 ${i+1}：${account} ==========`);
    const token = await login(account, pwd);
    if (token) {
      console.log(await signIn(token));
      await new Promise(r => setTimeout(r, 1000));
      console.log(await getBalance(token));
    }
    await new Promise(r => setTimeout(r, 1000));
  }
})();