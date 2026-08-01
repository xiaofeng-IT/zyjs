// 使用说明：
// 1. 在运行前设置环境变量名称 ZSP，值：定义备注#secretId#secretKey#deviceId。
// 2. 数值入口：面板进入商户密匙模块获取 SecretId#SecretKey，并填写设备码。
// 3. 多账号请使用换行分隔。
// 4. 可选：设置环境变量 ZSP_WEB，格式：备注#手机号#密码（多账号换行或&分隔）。
//    备注需与 ZSP 中的备注一致，用于查询金币余额和账户余额。
//    示例：8410#13812345678#mypassword
// 5. 可选环境变量：ZSP_MAX_ADS 控制单账号最大执行次数，默认 50；ZSP_TIMEOUT 控制请求超时时间，默认 15000 毫秒。
// 6. 运行命令：node 中视频.js。
// 7. 注册链接：https://zspad.xvgad.com/#/register?inviteCode=ba5DT1RB
// 8. 下载：https://a.zsp55.app/
// 9. 免责声明：本内容仅为互联网项目资讯分享，不构成任何投资建议。平台规则、奖励机制、活动内容可能随时调整，请以官方公告为准。参与者需自行判断风险，理性参与。请勿借贷、充值或投入超出自身承受能力的资金。本人仅作信息分享，不对平台后续运营及相关结果承担责任。


const http = require("http");
const https = require("https");

const ENV_NAME = "中视频";
const BASE_URL = "https://x1.zsptv.online";
const USER_AGENT = "Mozilla/5.0 (Linux; Android 15; 23013RK75C Build/AQ3A.250226.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.260 Mobile Safari/537.36 (Immersed/39.42857) Html5Plus/1.0";
const REQUEST_TIMEOUT = readPositiveInteger(process.env.ZSP_TIMEOUT, 15000);
const MAX_ADS = readPositiveInteger(process.env.ZSP_MAX_ADS, 50);
const ACCOUNT_ENV_NAMES = ["ZSP", "AD_WATCH_ACCOUNTS"];
const MAX_CONSECUTIVE_FAILURES = 3; // 单个账号最大连续失败次数，达到后停止该账号

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function readPositiveInteger(value, fallback) {
  const num = Number.parseInt(value, 10);
  return Number.isFinite(num) && num > 0 ? num : fallback;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function createRequestId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function maskValue(value) {
  if (!value) return "";
  const text = String(value);
  if (text.length <= 8) return "***";
  return `${text.slice(0, 4)}***${text.slice(-4)}`;
}

function sanitizeErrorMessage(message) {
  return String(message || "未知错误")
    .replace(/Bearer\s+[A-Za-z0-9._\-]+/gi, "Bearer ***")
    .replace(/secretKey[=:]\s*[^\s,#&]+/gi, "secretKey=***")
    .replace(/token[=:]\s*[^\s,#&]+/gi, "token=***");
}

function log(level, message, meta = {}) {
  const safeMeta = { ...meta };
  for (const key of Object.keys(safeMeta)) {
    if (/token|authorization|cookie|secret/i.test(key)) {
      safeMeta[key] = maskValue(safeMeta[key]);
    }
  }
  const suffix = Object.keys(safeMeta).length ? ` ${JSON.stringify(safeMeta)}` : "";
  console.log(`[${new Date().toISOString()}] [${level}] ${message}${suffix}`);
}

function decodeUnicode(str) {
  if (!str) return "";
  return String(str).replace(/\\u[\dA-F]{4}/gi, match => String.fromCharCode(Number.parseInt(match.replace(/\\u/g, ""), 16)));
}

function parseJson(text, fallback = null) {
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

function buildDeviceHeader(account) {
  return JSON.stringify({
    id: account.deviceId,
    brand: "xiaomi",
    model: "23013RK75C",
    platform: "android",
    system: "Android 15"
  });
}

function buildHeaders(account, token = "") {
  const headers = {
    Accept: "*/*",
    "User-Agent": USER_AGENT,
    "app-device": buildDeviceHeader(account),
    "Content-Type": "application/json",
    Host: "x1.zsptv.online"
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

async function httpRequest(options) {
  const requestId = options.requestId || createRequestId();
  const url = new URL(options.url);
  const transport = url.protocol === "https:" ? https : http;
  const body = options.body || "";

  return new Promise((resolve, reject) => {
    const req = transport.request({
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? 443 : 80),
      path: url.pathname + url.search,
      method: options.method || "GET",
      headers: options.headers || {},
      timeout: options.timeout || REQUEST_TIMEOUT
    }, res => {
      let data = "";

      res.setEncoding("utf8");
      res.on("data", chunk => {
        data += chunk;
      });
      res.on("end", () => {
        resolve({
          requestId,
          statusCode: res.statusCode,
          headers: res.headers,
          body: data
        });
      });
    });

    req.on("timeout", () => {
      req.destroy(new Error(`请求超时 ${REQUEST_TIMEOUT}ms`));
    });

    req.on("error", err => {
      err.requestId = requestId;
      reject(err);
    });

    if (body) {
      req.write(body);
    }

    req.end();
  });
}

async function requestJson(options) {
  const requestId = createRequestId();
  try {
    const response = await httpRequest({ ...options, requestId });
    const data = parseJson(response.body);
    const summary = response.body ? response.body.slice(0, 160) : "";

    log("INFO", "请求完成", {
      requestId,
      method: options.method || "GET",
      path: new URL(options.url).pathname,
      statusCode: response.statusCode
    });

    if (response.statusCode < 200 || response.statusCode >= 300) {
      log("WARNING", "响应状态异常", {
        requestId,
        statusCode: response.statusCode,
        summary: sanitizeErrorMessage(summary)
      });
    }

    if (!data) {
      return {
        ok: false,
        requestId,
        statusCode: response.statusCode,
        data: null,
        message: "响应不是有效 JSON"
      };
    }

    return {
      ok: response.statusCode >= 200 && response.statusCode < 300,
      requestId,
      statusCode: response.statusCode,
      data,
      message: decodeUnicode(data.message || "")
    };
  } catch (error) {
    log("ERROR", "请求异常", {
      requestId,
      message: sanitizeErrorMessage(error.message)
    });
    return {
      ok: false,
      requestId,
      statusCode: 0,
      data: null,
      message: sanitizeErrorMessage(error.message)
    };
  }
}

function loadAccounts() {
  const accounts = [];
  let envValue = "";
  let matchedEnvName = "";

  for (const envName of ACCOUNT_ENV_NAMES) {
    if (process.env[envName]) {
      envValue = process.env[envName];
      matchedEnvName = envName;
      break;
    }
  }

  if (!envValue) {
    log("WARNING", "请设置环境变量 ZSP 或 AD_WATCH_ACCOUNTS");
    return accounts;
  }

  log("INFO", "读取账号配置", { envName: matchedEnvName });

  const rows = envValue.split("\n").map(item => item.trim()).filter(Boolean);

  rows.forEach((row, index) => {
    const parts = row.split("#").map(item => item.trim());
    if (parts.length < 4 || !parts[1] || !parts[2] || !parts[3]) {
      log("WARNING", "忽略格式错误的账号配置", { index: index + 1 });
      return;
    }

    accounts.push({
      remark: parts[0] || `账号${index + 1}`,
      secretId: parts[1],
      secretKey: parts[2],
      deviceId: parts[3]
    });

    log("INFO", "账号配置已加载", {
      index: index + 1,
      remark: parts[0] || `账号${index + 1}`,
      secretId: maskValue(parts[1]),
      deviceId: maskValue(parts[3])
    });
  });

  return accounts;
}

async function login(account) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/auth/secretKeyLogin`,
    method: "POST",
    headers: buildHeaders(account),
    body: JSON.stringify({
      secretId: account.secretId,
      secretKey: account.secretKey
    })
  });

  if (!result.ok) {
    log("ERROR", "登录请求失败", {
      requestId: result.requestId,
      remark: account.remark,
      statusCode: result.statusCode,
      message: result.message
    });
    return "";
  }

  if (result.data.code === 0 && result.data.data && result.data.data.token) {
    log("INFO", "登录成功", {
      requestId: result.requestId,
      remark: account.remark,
      token: result.data.data.token
    });
    return result.data.data.token;
  }

  log("ERROR", "登录失败", {
    requestId: result.requestId,
    remark: account.remark,
    message: result.message || "未知错误"
  });
  return "";
}

async function checkAndSign(token, account) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/device/userSign`,
    method: "POST",
    headers: buildHeaders(account, token),
    body: "{}"
  });

  if (!result.ok) {
    log("ERROR", "签到请求失败", {
      requestId: result.requestId,
      remark: account.remark,
      statusCode: result.statusCode,
      message: result.message
    });
    return false;
  }

  if (result.data.code === 0) {
    log("INFO", "签到成功", {
      requestId: result.requestId,
      remark: account.remark,
      message: result.message,
      reward: result.data.data?.qiandao_money || 0,
      continuousDays: result.data.data?.continuousDays || 1
    });
    return true;
  }

  if (result.message.includes("已签到")) {
    log("INFO", "今日已签到", {
      requestId: result.requestId,
      remark: account.remark
    });
    return true;
  }

  log("ERROR", "签到失败", {
    requestId: result.requestId,
    remark: account.remark,
    message: result.message || "未知错误"
  });
  return false;
}

async function getNextAd(token, account) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/ad/next`,
    method: "GET",
    headers: buildHeaders(account, token)
  });

  if (!result.ok) {
    log("ERROR", "获取广告失败", {
      requestId: result.requestId,
      remark: account.remark,
      statusCode: result.statusCode,
      message: result.message
    });
    return null;
  }

  if (result.data.code !== 0 || !result.data.data || !result.data.data.result) {
    log("WARNING", "未获取到广告数据", {
      requestId: result.requestId,
      remark: account.remark,
      message: result.message || "未知错误"
    });
    return null;
  }

  const ad = result.data.data.result;
  return {
    id: ad.id,
    title: decodeUnicode(ad.title),
    description: decodeUnicode(ad.description),
    duration: readPositiveInteger(ad.video?.duration, 30),
    videoUrl: ad.video?.url || "",
    playUrl: ad.video?.play_url || "",
    reward: ad.reward || 0
  };
}

async function startVideoPlay(token, account, adId, playTime) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/ad/video/play`,
    method: "POST",
    headers: buildHeaders(account, token),
    body: JSON.stringify({
      clientIp: "",
      deviceInfo: {
        deviceId: account.deviceId,
        platform: "android"
      },
      id: String(adId),
      playTime
    })
  });

  if (!result.ok) {
    log("ERROR", "开始播放请求失败", {
      requestId: result.requestId,
      remark: account.remark,
      statusCode: result.statusCode,
      message: result.message
    });
    return null;
  }

  if (result.data.code === 0 && result.data.data && result.data.data.id) {
    return {
      playRecordId: result.data.data.id,
      initialReward: result.data.data.reward || 0,
      reward: result.data.data.reward || 0
    };
  }

  log("ERROR", "开始播放失败", {
    requestId: result.requestId,
    remark: account.remark,
    message: result.message || "未知错误"
  });
  return null;
}

async function endVideoPlay(token, account, playRecordId) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/ad/video/ended`,
    method: "POST",
    headers: buildHeaders(account, token),
    body: JSON.stringify({
      clientIp: "",
      deviceInfo: {
        deviceId: account.deviceId,
        platform: "android"
      },
      id: String(playRecordId),
      playTime: new Date().toISOString()
    })
  });

  if (!result.ok) {
    log("WARNING", "结束确认请求失败", {
      requestId: result.requestId,
      remark: account.remark,
      statusCode: result.statusCode,
      message: result.message
    });
    return false;
  }

  if (result.data.code === 0) {
    return true;
  }

  log("WARNING", "结束确认返回异常", {
    requestId: result.requestId,
    remark: account.remark,
    message: result.message || "未知错误"
  });
  return false;
}

const WEB_BASE = "https://x1.zsptv.online";
const WEB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

// 加载 Web 账号（ZSP_WEB 环境变量，格式：备注#手机号#密码，多账号换行或&分隔）
// Web 账号与 App 账号通过 remark 匹配（remark 相同则关联）
function loadWebAccounts() {
  const envValue = (process.env.ZSP_WEB || "").trim();
  if (!envValue) return [];

  const webAccounts = {};
  const rows = envValue.split(/[\n&]/).map(s => s.trim()).filter(Boolean);

  rows.forEach((row, index) => {
    const parts = row.split("#").map(s => s.trim());
    if (parts.length < 3 || !parts[1] || !parts[2]) {
      log("WARNING", "ZSP_WEB 格式错误，已忽略", { index: index + 1, hint: "格式：备注#手机号#密码" });
      return;
    }
    const remark = parts[0] || `web账号${index + 1}`;
    webAccounts[remark] = { phone: parts[1], password: parts[2] };
    log("INFO", "Web账号配置已加载", { index: index + 1, remark, phone: maskValue(parts[1]) });
  });

  return webAccounts;
}

const WEB_ACCOUNTS = loadWebAccounts();

async function webPasswordLogin(remark) {
  const cred = WEB_ACCOUNTS[remark];
  if (!cred) {
    // 没有对应 Web 账号，静默跳过
    return null;
  }

  const result = await requestJson({
    url: `${WEB_BASE}/api/web/v1/auth/passwordLogin`,
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": WEB_UA,
      Origin: "https://zspad.xvgad.com",
      Referer: "https://zspad.xvgad.com/"
    },
    body: JSON.stringify({ mobile: cred.phone, password: cred.password })
  });

  if (result.ok && result.data?.code === 0 && result.data?.data?.token) {
    log("INFO", "Web端登录成功", { remark });
    return result.data.data.token;
  }

  log("WARNING", "Web端登录失败", {
    remark,
    code: result.data?.code,
    message: result.message
  });
  return null;
}

function buildWebHeaders(webToken) {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    "User-Agent": WEB_UA,
    Authorization: `bearer ${webToken}`,
    Origin: "https://zspad.xvgad.com",
    Referer: "https://zspad.xvgad.com/"
  };
}

async function getUserInfo(token, account) {
  const webToken = await webPasswordLogin(account.remark);
  if (!webToken) {
    log("WARNING", "跳过余额查询（未配置 ZSP_WEB 或登录失败）", { remark: account.remark });
    return null;
  }

  const webHeaders = buildWebHeaders(webToken);

  const walletResult = await requestJson({
    url: `${WEB_BASE}/api/web/v1/user/wallet/score/getInfo`,
    method: "GET",
    headers: webHeaders
  });

  if (walletResult.ok && walletResult.data?.code === 0 && walletResult.data?.data) {
    const info = walletResult.data.data;
    log("INFO", "Web端金币查询成功", { remark: account.remark });

    // 查账户余额（人民币）
    const balanceResult = await requestJson({
      url: `${WEB_BASE}/api/web/v1/user/wallet/balance/getInfo`,
      method: "GET",
      headers: webHeaders
    });

    let moneyBalance = 0;
    if (balanceResult.ok && balanceResult.data?.code === 0 && balanceResult.data?.data) {
      moneyBalance = Number(balanceResult.data.data.balance) || 0;
    }

    return {
      coins: Number(info.balance) || 0,
      balance: moneyBalance,
      _webHeaders: webHeaders
    };
  }

  log("WARNING", "Web端余额查询失败", {
    remark: account.remark,
    code: walletResult.data?.code,
    message: walletResult.message
  });
  return null;
}

async function getTodayCoins(token, account, userInfo) {
  const webHeaders = userInfo?._webHeaders;
  if (!webHeaders) return null;

  const result = await requestJson({
    url: `${WEB_BASE}/api/web/v1/dashboard/getPanelData`,
    method: "GET",
    headers: webHeaders
  });

  if (result.ok && result.data?.code === 0 && result.data?.data != null) {
    const d = result.data.data;
    return d.incomeScore ?? null;
  }

  return null;
}

async function autoWithdraw(account, userInfo) {
  const threshold = 10;
  const webHeaders = userInfo?._webHeaders;
  if (!webHeaders) return { withdrawn: false, amount: 0, reason: "无Web会话" };

  const balance = userInfo.balance;
  if (balance < threshold) {
    log("INFO", "余额不足，跳过提现", { remark: account.remark, balance, threshold });
    return { withdrawn: false, amount: 0, reason: `余额 ¥${balance.toFixed(2)} 未达 ¥${threshold}` };
  }

  const amount = balance.toFixed(2);
  log("INFO", "余额已达提现阈值，发起提现", { remark: account.remark, balance, threshold, amount });

  const result = await requestJson({
    url: `${WEB_BASE}/api/web/v1/user/wallet/balance/withdraw`,
    method: "POST",
    headers: webHeaders,
    body: JSON.stringify({ amount })
  });

  if (result.ok && result.data?.code === 0) {
    log("INFO", "提现成功", { remark: account.remark, amount });
    return { withdrawn: true, amount: Number(amount), reason: "成功" };
  }

  log("WARNING", "提现失败", {
    remark: account.remark,
    amount,
    code: result.data?.code,
    message: result.message
  });
  return { withdrawn: false, amount: 0, reason: result.message || "接口返回失败" };
}


async function claimReward(token, account, adInfo) {
  const startTime = new Date().toISOString();

  log("INFO", "开始播放广告", {
    remark: account.remark,
    adId: adInfo.id,
    title: adInfo.title,
    duration: adInfo.duration,
    reward: adInfo.reward
  });

  const playResult = await startVideoPlay(token, account, adInfo.id, startTime);
  if (!playResult || !playResult.playRecordId) {
    return { success: false, reward: 0 };
  }

  log("INFO", "播放记录已创建", {
    remark: account.remark,
    playRecordId: playResult.playRecordId,
    initialReward: playResult.initialReward
  });

  await wait(adInfo.duration * 1000);

  const ended = await endVideoPlay(token, account, playResult.playRecordId);
  if (!ended) {
    return {
      success: false,
      reward: 0,
      playRecordId: playResult.playRecordId
    };
  }

  return {
    success: true,
    reward: playResult.reward || 0,
    playRecordId: playResult.playRecordId
  };
}

async function getTurntableInfo(token, account) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/device/getTurntableInfo`,
    method: "GET",
    headers: buildHeaders(account, token)
  });

  if (result.ok && result.data?.code === 0 && result.data?.data) {
    return {
      turntableNum: result.data.data.turntable_num ?? 0,
      turntableMoney: result.data.data.turntable_money ?? 0
    };
  }
  return null;
}

async function doTurntable(token, account) {
  const result = await requestJson({
    url: `${BASE_URL}/api/app/v1/device/turntable`,
    method: "POST",
    headers: buildHeaders(account, token),
    body: JSON.stringify({})
  });

  if (result.ok && result.data?.code === 0) {
    const reward = result.data.data ?? 0;
    log("INFO", "抽奖成功", {
      remark: account.remark,
      reward,
      message: result.message
    });
    return { success: true, reward };
  }

  log("WARNING", "抽奖失败", {
    remark: account.remark,
    code: result.data?.code,
    message: result.message
  });
  return { success: false, reward: 0 };
}

async function runTurntable(token, account) {
  const info = await getTurntableInfo(token, account);
  if (!info) {
    log("WARNING", "获取抽奖信息失败", { remark: account.remark });
    return { totalDraws: 0, totalReward: 0 };
  }

  const { turntableNum } = info;
  if (turntableNum <= 0) {
    log("INFO", "暂无抽奖次数", { remark: account.remark });
    return { totalDraws: 0, totalReward: 0 };
  }

  log("INFO", "发现抽奖次数，开始抽奖", { remark: account.remark, turntableNum });

  let totalDraws = 0;
  let totalReward = 0;
  for (let i = 0; i < turntableNum; i++) {
    const draw = await doTurntable(token, account);
    if (draw.success) {
      totalDraws++;
      totalReward += Number(draw.reward) || 0;
    }
    if (i < turntableNum - 1) await wait(randomInt(1000, 2000));
  }

  log("INFO", "抽奖完成", { remark: account.remark, totalDraws, totalReward });
  return { totalDraws, totalReward };
}

/**
 * 处理单个账号，支持并发执行
 * 账号运行失败3次后停止该账号
 */
async function processAccount(account) {
  let token = await login(account);
  if (!token) {
    log("ERROR", "登录失败，跳过账号", { remark: account.remark });
    return { success: false, reason: "login_failed" };
  }

  const signed = await checkAndSign(token, account);
  if (!signed) {
    log("ERROR", "签到未完成，跳过账号", { remark: account.remark });
    return { success: false, reason: "sign_failed" };
  }

  // 签到后检查并执行抽奖
  const turntableResult = await runTurntable(token, account);

  let successCount = 0;
  let failCount = 0;
  let totalReward = 0;
  let consecutiveFailures = 0;
  let shouldStop = false;

  for (let adCount = 0; adCount < MAX_ADS && !shouldStop; adCount++) {
    log("INFO", "开始处理任务", {
      remark: account.remark,
      current: adCount + 1,
      total: MAX_ADS,
      consecutiveFailures
    });

    // 连续失败达到上限，停止该账号
    if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
      log("WARNING", "连续失败次数已达上限，停止该账号", {
        remark: account.remark,
        maxFailures: MAX_CONSECUTIVE_FAILURES,
        totalSuccess: successCount,
        totalReward
      });
      shouldStop = true;
      break;
    }

    // 尝试刷新登录状态（仅在需要时）
    if (consecutiveFailures > 0 && consecutiveFailures % 2 === 0) {
      log("INFO", "尝试刷新登录状态", { remark: account.remark });
      const newToken = await login(account);
      if (newToken) {
        token = newToken;
        log("INFO", "登录状态刷新成功", { remark: account.remark });
      } else {
        log("WARNING", "登录状态刷新失败", { remark: account.remark });
        consecutiveFailures++;
        await wait(randomInt(2500, 5000));
        continue;
      }
    }

    const adInfo = await getNextAd(token, account);
    if (!adInfo) {
      consecutiveFailures++;
      failCount++;
      log("WARNING", "获取广告失败", {
        remark: account.remark,
        consecutiveFailures
      });
      await wait(randomInt(2500, 5000));
      continue;
    }

    const playResult = await claimReward(token, account, adInfo);
    if (playResult.success) {
      successCount++;
      totalReward += Number.parseInt(playResult.reward, 10) || 0;
      consecutiveFailures = 0; // 成功后重置连续失败计数
      log("INFO", "任务完成", {
        remark: account.remark,
        reward: playResult.reward || 0,
        playRecordId: playResult.playRecordId,
        totalRewardSoFar: totalReward
      });
    } else {
      consecutiveFailures++;
      failCount++;
      log("WARNING", "任务失败", {
        remark: account.remark,
        consecutiveFailures,
        maxBeforeStop: MAX_CONSECUTIVE_FAILURES
      });
    }

    if (adCount < MAX_ADS - 1 && !shouldStop) {
      const delay = randomInt(3000, 6000);
      log("INFO", "等待后继续", {
        remark: account.remark,
        delaySeconds: Math.round(delay / 1000),
        remaining: MAX_ADS - (adCount + 1)
      });
      await wait(delay);
    }
  }

  const finalMessage = shouldStop
    ? `连续失败${MAX_CONSECUTIVE_FAILURES}次后停止`
    : "完成所有任务";

  log("INFO", `账号处理完成 (${finalMessage})`, {
    remark: account.remark,
    successCount,
    failCount,
    totalReward,
    totalAttempts: successCount + failCount,
    successRate: successCount + failCount > 0 ? `${((successCount / (successCount + failCount)) * 100).toFixed(1)}%` : "0%"
  });

  // 查询今日金币奖励、金币余额、账户余额，并尝试自动提现
  let userInfo = null;
  let todayCoins = null;
  let withdrawResult = null;
  try {
    userInfo = await getUserInfo(token, account);
    todayCoins = await getTodayCoins(token, account, userInfo);
    if (userInfo) {
      log("INFO", "账户信息", {
        remark: account.remark,
        今日金币奖励: todayCoins ?? totalReward,
        金币余额: userInfo.coins,
        账户余额: userInfo.balance
      });
      withdrawResult = await autoWithdraw(account, userInfo);
    }
  } catch (e) {
    log("WARNING", "查询账户信息异常", { remark: account.remark, message: e.message });
  }

  return {
    success: true,
    remark: account.remark,
    successCount,
    failCount,
    totalReward,
    stoppedEarly: shouldStop,
    userInfo,
    todayCoins,
    withdrawResult,
    turntableResult
  };
}

/**
 * 主函数：并发处理所有账号
 * 使用 Promise.allSettled 确保所有账号都被处理，互不影响
 */
async function main() {
  log("INFO", "脚本开始运行（并发模式）", {
    envName: ENV_NAME,
    maxAds: MAX_ADS,
    timeout: REQUEST_TIMEOUT,
    maxConsecutiveFailures: MAX_CONSECUTIVE_FAILURES
  });

  const accounts = loadAccounts();
  if (accounts.length === 0) {
    log("ERROR", "未找到有效账号配置");
    return;
  }

  log("INFO", `准备并发处理 ${accounts.length} 个账号`);

  // 并发处理所有账号
  const startTime = Date.now();
  const results = await Promise.allSettled(
    accounts.map(async (account, index) => {
      // 随机延迟 0-300 秒后开始签到，避免多账号同时触发
      const startDelaySec = randomInt(0, 300);
      log("INFO", "等待随机延迟后开始签到", {
        index: index + 1,
        total: accounts.length,
        remark: account.remark,
        delaySeconds: startDelaySec
      });
      await wait(startDelaySec * 1000);

      log("INFO", "开始处理账号", {
        index: index + 1,
        total: accounts.length,
        remark: account.remark
      });

      try {
        const result = await processAccount(account);
        return { accountRemark: account.remark, result };
      } catch (error) {
        log("ERROR", "账号处理异常", {
          remark: account.remark,
          message: sanitizeErrorMessage(error.message)
        });
        return {
          accountRemark: account.remark,
          error: error.message,
          result: { success: false, reason: "exception" }
        };
      }
    })
  );

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  // 汇总统计
  let totalSuccessCount = 0;
  let totalRewardSum = 0;
  let accountsCompleted = 0;
  let accountsFailed = 0;
  let accountsStoppedEarly = 0;

  log("INFO", "========== 运行结果汇总 ==========");

  for (const settled of results) {
    if (settled.status === "fulfilled") {
      const { accountRemark, result, error } = settled.value;
      if (error || !result?.success) {
        accountsFailed++;
        log("WARNING", `账号 [${accountRemark}] 处理失败`, { error: error || "未知错误" });
      } else {
        accountsCompleted++;
        totalSuccessCount += result.successCount || 0;
        totalRewardSum += result.totalReward || 0;
        if (result.stoppedEarly) {
          accountsStoppedEarly++;
        }
        log("INFO", `账号 [${accountRemark}] 处理成功`, {
          successCount: result.successCount,
          totalReward: result.totalReward,
          stoppedEarly: result.stoppedEarly
        });
      }
    } else {
      accountsFailed++;
      log("ERROR", "账号处理 Promise 被拒绝", {
        reason: sanitizeErrorMessage(settled.reason)
      });
    }
  }

  log("INFO", "========== 最终统计 ==========");
  log("INFO", "执行概况", {
    总账号数: accounts.length,
    成功完成账号数: accountsCompleted,
    失败账号数: accountsFailed,
    提前停止账号数: accountsStoppedEarly,
    总成功任务数: totalSuccessCount,
    总获得奖励: totalRewardSum,
    总耗时_秒: elapsed
  });

  log("INFO", "所有账号处理完成");

  // ========== 青龙通知 ==========
  try {
    const notifyLines = [];
    notifyLines.push(`📊 执行时间：${elapsed} 秒`);
    notifyLines.push(`👥 账号总数：${accounts.length} 个（成功 ${accountsCompleted}，失败 ${accountsFailed}${accountsStoppedEarly > 0 ? `，提前停止 ${accountsStoppedEarly}` : ""}）`);
    notifyLines.push(`✅ 总成功任务：${totalSuccessCount} 次`);
    notifyLines.push(`🎁 本次总获得奖励：${totalRewardSum} 金币`);
    notifyLines.push("");

    for (const settled of results) {
      if (settled.status === "fulfilled") {
        const { accountRemark, result } = settled.value;
        if (!result?.success) continue;
        const thisReward = result.totalReward;
        const todayCoinsVal = result.todayCoins != null ? result.todayCoins : "–";
        const coinsBalance = result.userInfo?.coins != null ? result.userInfo.coins : "–";
        const moneyBalance = result.userInfo?.balance != null ? `¥${Number(result.userInfo.balance).toFixed(2)}` : "–";
        notifyLines.push(`🔖 账号：${accountRemark}`);
        notifyLines.push(`   🎯 本次金币奖励：${thisReward}`);
        notifyLines.push(`   📺 今日金币奖励：${todayCoinsVal}`);
        if (result.turntableResult?.totalDraws > 0) {
          notifyLines.push(`   🎰 抽奖：${result.turntableResult.totalDraws} 次，获得 ${result.turntableResult.totalReward} 金币`);
        }
        notifyLines.push(`   💰 金币余额：${coinsBalance}`);
        notifyLines.push(`   💳 账户余额：${moneyBalance}`);
        if (result.withdrawResult?.withdrawn) {
          notifyLines.push(`   💸 自动提现：¥${result.withdrawResult.amount.toFixed(2)} ✅`);
        } else if (result.withdrawResult && !result.withdrawResult.withdrawn && result.withdrawResult.reason !== "已禁用" && result.withdrawResult.reason !== "无Web会话") {
          notifyLines.push(`   💸 提现未触发：${result.withdrawResult.reason}`);
        }
        if (result.stoppedEarly) {
          notifyLines.push(`   ⚠️ 因连续失败提前终止`);
        }
      }
    }

    const notifyTitle = `中视频脚本运行完成`;
    const notifyContent = notifyLines.join("\n");

    // 青龙通知兼容多种调用方式
    if (typeof $notify === "function") {
      $notify(notifyTitle, "", notifyContent);
    } else if (typeof notify === "function") {
      notify(notifyTitle, "", notifyContent);
    } else {
      // 尝试加载青龙内置通知模块
      try {
        const { sendNotify } = require("./sendNotify");
        await sendNotify(notifyTitle, notifyContent);
      } catch {
        try {
          const { sendNotify } = require("/ql/scripts/sendNotify");
          await sendNotify(notifyTitle, notifyContent);
        } catch {
          log("INFO", "未检测到青龙通知模块，通知内容如下：");
          log("INFO", `[${notifyTitle}]\n${notifyContent}`);
        }
      }
    }
  } catch (notifyError) {
    log("WARNING", "发送通知时发生异常", { message: notifyError.message });
  }
}

if (require.main === module) {
  main().catch(error => {
    log("ERROR", "脚本异常退出", {
      message: sanitizeErrorMessage(error.message)
    });
    process.exitCode = 1;
  });
}