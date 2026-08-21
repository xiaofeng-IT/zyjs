const axios = require('axios');
const fs = require('fs');
const path = require('path');

// ===================== 全局配置（原样） =====================
const MAX_ACCOUNT = 120;
const AD_ROUND_PER_ACCOUNT = 120;
const BASE_URL = 'https://x1.zsptv.online/api/app/v1';
const CACHE_DIR = path.join(__dirname, 'acc_cache');
if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR);
const MAX_RETRY = 3;

// ===================== 随机设备库 =====================
const DEVICE_BRANDS = ["xiaomi", "huawei", "samsung", "oppo", "vivo", "realme", "oneplus"];
const ANDROID_VERSIONS = ["Android 13", "Android 14", "Android 15", "Android 16"];

// ===================== 缓存（修复版） =====================
function getDeviceCachePath(deviceId) {
    return path.join(CACHE_DIR, `device_${deviceId}.json`);
}

function loadDeviceCache(deviceId) {
    const file = getDeviceCachePath(deviceId);
    if (!fs.existsSync(file)) return null;
    try {
        const data = JSON.parse(fs.readFileSync(file, 'utf8'));
        if (data && data.device && data.ua) return data;
        return null;
    } catch {
        return null;
    }
}

function saveDeviceCache(deviceId, device, ua) {
    const data = { device, ua };
    fs.writeFileSync(getDeviceCachePath(deviceId), JSON.stringify(data, null, 2));
}

// ===================== 生成随机设备（修复版） =====================
function generateRandomDevice(customDeviceId) {
    const randomBrand = DEVICE_BRANDS[Math.floor(Math.random() * DEVICE_BRANDS.length)];
    const randomModel = Math.random().toString(16).slice(2, 22).toUpperCase();
    const randomSystem = ANDROID_VERSIONS[Math.floor(Math.random() * ANDROID_VERSIONS.length)];
    return {
        id: customDeviceId,
        brand: randomBrand,
        model: randomModel,
        platform: "android",
        system: randomSystem
    };
}

// ===================== UA =====================
function randomUA(device) {
    const chromeVer = ["135.0.7049.42","136.0.7091.81","137.0.7151.115","138.0.7204.63"];
    const wvNum = Math.floor(Math.random() * 20 + 20);
    return `Mozilla/5.0 (Linux; ${device.system}; ${device.model} Build/BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/${chromeVer[Math.floor(Math.random()*chromeVer.length)]} Mobile Safari/537.36 (Immersed/${wvNum}.0) Html5Plus/1.0`;
}

// ===================== 获取账号设备（最终修复） =====================
function getAccInfo(accIdx, customDeviceId) {
    const cache = loadDeviceCache(customDeviceId);
    if (cache) {
        return {
            device: cache.device,
            ua: cache.ua
        };
    }

    const dev = generateRandomDevice(customDeviceId);
    const ua = randomUA(dev);
    saveDeviceCache(customDeviceId, dev, ua);
    return { device: dev, ua: ua };
}

// ===================== 公共工具 =====================
function getRandomSeconds() {
    const min = 45;
    const max = 60;
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getGap(accIdx) {
    const env = process.env[`GAP_SECONDS_${accIdx}`];
    if (!env) return getRandomSeconds();
    if (env.includes('-')) {
        const [minStr, maxStr] = env.split('-').map(s => s.trim());
        const min = parseInt(minStr);
        const max = parseInt(maxStr);
        if (!isNaN(min) && !isNaN(max) && min < max) {
            return Math.floor(Math.random() * (max - min + 1)) + min;
        }
    }
    const num = parseInt(env);
    return isNaN(num) ? getRandomSeconds() : num;
}

async function countDown(seconds, prefix = "等待") {
    for (let i = seconds; i > 0; i--) {
        process.stdout.write(`\r⏳ ${prefix}：${i} 秒`);
        await new Promise(r => setTimeout(r, 1000));
    }
    process.stdout.write(`\r✅ ${prefix}：已完成！${' '.repeat(20)}\n`);
}

// ===================== 日志 =====================
const log = {
    info: (a, m) => console.log(`ℹ️【账号${a}】${m}`),
    success: (a, m) => console.log(`✅【账号${a}】${m}`),
    error: (a, m) => console.log(`❌【账号${a}】${m}`),
    step: (a, m) => console.log(`➡️【账号${a}】${m}`),
    done: (a, m) => console.log(`🎉【账号${a}】${m}`)
};

// ===================== 请求头 =====================
function getHeaders(token, device, ua) {
    return {
        'Authorization': token ? `Bearer ${token}` : '',
        'User-Agent': ua,
        'app-device': JSON.stringify(device),
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Host': 'x1.zsptv.online',
        'Connection': 'Keep-Alive'
    };
}

// ===================== 签到功能 =====================
async function checkAndSign(accIdx, session) {
    try {
        log.step(accIdx, "查询签到状态");
        const info = await session.get("/device/getSignInfo");
        if (info.data.code !== 0) {
            log.error(accIdx, "查询签到失败：" + info.data.message);
            return;
        }
        if (info.data.data.is_today_sign === 1) {
            log.success(accIdx, "今日已签到，跳过");
            return;
        }
        log.step(accIdx, "执行签到");
        const sign = await session.post("/device/userSign", {});
        if (sign.data.code === 0) {
            log.success(accIdx, `签到成功，获得${sign.data.data.qiandao_money}金币，连续签到${sign.data.data.continuousDays}天`);
        } else {
            log.error(accIdx, "签到失败：" + sign.data.message);
        }
    } catch (e) {
        log.error(accIdx, "签到异常：" + e.message);
    }
}

// ===================== 广告任务 =====================
async function doAdRound(accIdx, session, device, r) {
    let retry = 0;
    while (retry < MAX_RETRY) {
        try {
            await new Promise(resolve => setTimeout(resolve, 3000 + Math.random() * 5000));
            log.info(accIdx, `——— 第${r}轮广告 ———`);
            const adRes = await session.get(`/ad/next`);
            const ad = adRes.data?.data?.result;
            if (!ad) {
                log.error(accIdx, `第${r}轮异常：暂无可用广告`);
                const waitTime = Math.floor(Math.random() * 20) + 30;
                log.info(accIdx, `失败等待：${waitTime} 秒`);
                await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
                log.info(accIdx, `广告已达上限，账号任务终止`);
                return { done: true, reward: 0 };
            }
            const watchTime = ad.video?.duration ? ad.video.duration : getRandomSeconds();
            log.info(accIdx, `广告观看时长: ${watchTime}s`);
            const playTime = new Date().toISOString();
            const playRes = await session.post(`/ad/video/play`,
                { clientIp: "", deviceInfo: { platform: "android" }, id: ad.id, playTime },
                { headers: { "Content-Type": "application/json" } }
            );
            if (playRes.data.code !== 0) throw new Error("播放开始上报失败");
            const rew = playRes.data.data.reward || 0;
            await countDown(watchTime, "广告播放中");
            const endRes = await session.post(`/ad/video/ended`,
                { clientIp: "", deviceInfo: { deviceId: device.id, platform: "android" }, id: playRes.data.data.id, playTime: new Date().toISOString() },
                { headers: { "Content-Type": "application/json" } }
            );
            if (endRes.data.code !== 0) throw new Error("播放结束上报失败");
            return { done: false, reward: rew };
        } catch (e) {
            retry++;
            log.error(accIdx, `第${r}轮异常: ${e.message}（重试 ${retry}/${MAX_RETRY}）`);
            const gap = getGap(accIdx);
            await countDown(gap, "失败等待");
            if (retry >= MAX_RETRY) {
                log.error(accIdx, `第${r}轮重试${MAX_RETRY}次失败，停止该账号`);
                return { done: true, reward: 0 };
            }
        }
    }
    return { done: true, reward: 0 };
}

// ===================== 单账号任务 =====================
async function accountTask(accIdx) {
    const keyEnv = process.env[`KEY_PAIR${accIdx}`] || "";
    if (!keyEnv) {
        return 0;
    }
    const parts = keyEnv.split("#");
    if (parts.length < 4) {
        log.error(accIdx, "环境变量格式错误");
        return 0;
    }
    const SECRET_ID = parts[0];
    const SECRET_KEY = parts[1];
    const customDeviceId = parts[3];

    // 核心修复：确保一定能拿到 device
    const { device, ua } = getAccInfo(accIdx, customDeviceId);

    log.info(accIdx, `设备ID: ${device.id}`);
    log.info(accIdx, `设备品牌: ${device.brand} | 型号: ${device.model} | 系统: ${device.system}`);
    log.info(accIdx, `专属UA已加载`);

    let totalReward = 0;
    let session;

    try {
        log.step(accIdx, "正在登录...");
        const loginRes = await axios.post(`${BASE_URL}/auth/secretKeyLogin`,
            { secretId: SECRET_ID, secretKey: SECRET_KEY },
            { headers: getHeaders("", device, ua) }
        );
        if (loginRes.data.code !== 0) throw new Error("登录校验失败");
        log.success(accIdx, "登录成功");
        const token = loginRes.data.data.token;
        session = axios.create({
            baseURL: BASE_URL,
            headers: getHeaders(token, device, ua)
        });
        await checkAndSign(accIdx, session);
        for (let r = 1; r <= AD_ROUND_PER_ACCOUNT; r++) {
            const { done, reward } = await doAdRound(accIdx, session, device, r);
            if (done) break;
            totalReward += reward;
            log.done(accIdx, `本轮奖励:${reward} 账号累计:${totalReward}`);
            if (r < AD_ROUND_PER_ACCOUNT) {
                const gap = getGap(accIdx);
                log.info(accIdx, `轮间间隙:${gap}秒`);
                await countDown(gap, "轮间等待");
            }
        }
    } catch (e) {
        log.error(accIdx, `账号整体任务失败: ${e.message}`);
    }
    log.success(accIdx, `账号全部完成，总奖励:${totalReward}`);
    return totalReward;
}

// ===================== 主程序 =====================
async function main() {
    console.log(`\n🚀 正在检测已配置账号...`);
    const validAccounts = [];
    for (let i = 1; i <= MAX_ACCOUNT; i++) {
        const env = process.env[`KEY_PAIR${i}`];
        if (env && env.split("#").length >= 4) {
            validAccounts.push(i);
        }
    }
    if (validAccounts.length === 0) {
        console.log("❌ 未检测到任何已配置的 KEY_PAIR 账号");
        return;
    }
    console.log(`✅ 检测到 ${validAccounts.length} 个有效账号，开始运行`);
    const taskList = validAccounts.map(idx => accountTask(idx));
    await Promise.all(taskList);
    console.log(`\n==================== 所有任务全部结束 ====================`);
}

main().catch(console.error);