// ==============================================
//  点盈广告上报脚本，QQ群：755514159
// ==============================================

/************可自定义配置区************/
const config = {
    token: "你自己的token",
    deviceId: "你自己的deviceid",
    oaid: "你自己的oaid",
    loopTimes: 100,           // 循环次数
    eCPMmin: 1500,            // 最小eCPM
    eCPMmax: 8000,            // 最大eCPM
    targetBalance: 20000,     // 目标余额
    version: "1105",
    
    // 新增的签名请求头（来自新的curl）
    sha: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJFQUQ5OTVFNkEwRjYzMEJFMUE0NTA2NDA4RUE0NUYwOUQ0MEIxQTkwIn0.yxmzqIbSO6CKnlXUOJ8vYf5c9InjNlONF-DYKF-rpOY",
    tokena: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMzAwZDI2MC1mMGJhLTQ1OWEtOGI4Mi0yYWYzODEwZGNlNGMifQ.RPC4NCnjYm9wl9uwgJWkB6womd9xmILlKOy_XUAMThE",
};

/************固定配置区************/
const apiHost = "yx1539.jiudianyin.cn";
const placementId = "19555666";
const network_firm_id = "21";

// API 接口
const userInfoApi = `https://${apiHost}/api/Member/GetUserinfo`;
const adReportApi = `https://${apiHost}/api/Sigbom/AOter`;
const adTypeApi = `https://${apiHost}/api/Sigbom/ATye`;

const https = require('https');
const { setTimeout: sleep } = require('timers/promises');

// 美化日志输出
console.clear();
console.log("=".repeat(60));
console.log("🚀 点盈广告上报脚本已启动 | QQ群：755514159");
console.log("📅 启动时间：" + new Date().toLocaleString());
console.log("🎯 目标余额：" + config.targetBalance);
console.log("🔁 循环次数：" + config.loopTimes);
console.log("💰 eCPM 范围：" + config.eCPMmin + " ~ " + config.eCPMmax);
console.log("=".repeat(60));

// HTTP 请求封装
const http = {
    get: function(url, options = {}) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const reqOptions = {
                hostname: urlObj.hostname,
                port: 443,
                path: urlObj.pathname + urlObj.search,
                method: 'GET',
                headers: {
                    "version": config.version,
                    ...options.headers
                },
                timeout: 15000
            };

            const req = https.request(reqOptions, (res) => {
                let data = '';
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        body: {
                            json: () => { try { return JSON.parse(data) } catch { return null } },
                            string: () => data
                        }
                    });
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('请求超时')) });
            req.end();
        });
    },

    post: function(url, data, options = {}) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const postData = new URLSearchParams(data).toString();

            const reqOptions = {
                hostname: urlObj.hostname,
                port: 443,
                path: urlObj.pathname + urlObj.search,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    "version": config.version,
                    ...options.headers
                },
                timeout: 20000
            };

            const req = https.request(reqOptions, (res) => {
                let responseData = '';
                res.on('data', (chunk) => { responseData += chunk; });
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        body: {
                            json: () => { try { return JSON.parse(responseData) } catch { return null } },
                            string: () => responseData
                        }
                    });
                });
            });
            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('请求超时')) });
            req.write(postData);
            req.end();
        });
    }
};

// 获取统一的请求头
function getHeaders() {
    return {
        host: apiHost,
        token: config.token,
        sha: config.sha,
        tokena: config.tokena,
        "user-agent": "okhttp/4.10.0"
    };
}

// 调用 ATye 接口
async function callATye(type) {
    try {
        const params = { ad_type: 1, type, deviceId: config.deviceId, oaid: config.oaid };
        const res = await http.post(adTypeApi, params, { headers: getHeaders() });
        console.log(`✅ ATye 接口调用成功 | 状态码：${res.statusCode}`);
        return true;
    } catch (e) {
        console.log(`❌ ATye 接口异常：${e.message}`);
        return false;
    }
}

// 查询余额
async function getBalance() {
    try {
        const res = await http.get(userInfoApi, { headers: getHeaders() });
        
        if (res.statusCode !== 200) {
            console.log(`⚠️ 余额查询失败 | 状态码：${res.statusCode}`);
            return null;
        }
        
        const json = res.body.json();
        if (!json) {
            console.log("⚠️ 余额接口返回非JSON格式");
            return null;
        }

        // 尝试从不同路径获取余额
        let balance = 0;
        if (json?.data?.userinfo?.forecast_gold) balance = json.data.userinfo.forecast_gold;
        else if (json?.data?.forecast_gold) balance = json.data.forecast_gold;
        else if (json?.forecast_gold) balance = json.forecast_gold;
        else if (json?.data?.gold) balance = json.data.gold;
        else if (json?.gold) balance = json.gold;

        console.log(`💰 当前余额：${balance}`);
        return Number(balance) || 0;
    } catch (e) {
        console.log("❌ 余额请求失败：", e.message);
        return null;
    }
}

// 生成 UUID
function genUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c == 'x' ? r : (r & 3 | 8)).toString(16);
    });
}

// 主函数
async function main() {
    console.log("\n[1/2] 正在查询初始余额...");
    let currentBalance = await getBalance() || 0;

    if (currentBalance >= config.targetBalance) {
        console.log("\n✅ 当前余额已达标，脚本自动结束");
        return;
    }

    console.log(`\n[2/2] 开始执行广告上报（共 ${config.loopTimes} 轮）`);
    console.log("-".repeat(60));

    for (let o = 1; o <= config.loopTimes; o++) {
        console.log(`\n📌 第 ${o}/${config.loopTimes} 轮上报`);
        
        try {
            // 调用ATye
            await callATye(2);
            await sleep(500);

            // 生成上报参数
            const loadId = genUUID();
            const eCPM = Math.round(config.eCPMmin + Math.random() * (config.eCPMmax - config.eCPMmin));
            
            const paramsObj = {
                networkPlacementId: placementId,
                placementId: placementId,
                networkId: network_firm_id,
                loadId,
                eCPM,
                version: config.version,
                dividends: "4",
                ad_type: "1",
                type: "4",
                deviceId: config.deviceId,
                oaid: config.oaid,
                sgin: config.sgin,
                tc: config.tc
            };

            console.log(`📊 eCPM：${eCPM} | loadId：${loadId.slice(0,18)}...`);

            // 广告上报
            const res = await http.post(adReportApi, paramsObj, { headers: getHeaders() });
            console.log(`✅ 上报完成 | 状态码：${res.statusCode}`);

            await sleep(2000);

            // 查询最新余额
            const newBalance = await getBalance();
            if (newBalance !== null) currentBalance = newBalance;

            // 达到目标自动停止
            if (currentBalance >= config.targetBalance) {
                console.log("\n🎉 已达到目标余额，脚本停止");
                return;
            }

        } catch (e) {
            console.log(`❌ 本轮执行异常：${e.message}，跳过本轮`);
            await sleep(5000);
            continue;
        }

        // 轮次间隔
        if (o < config.loopTimes) {
            const waitSec = Math.round((28000 + Math.random() * 7000) / 1000);
            console.log(`\n⏳ 等待 ${waitSec} 秒后执行下一轮...`);
            await sleep(waitSec * 1000);
        }
    }

    console.log("\n" + "=".repeat(60));
    console.log("🎊 全部任务执行完成");
    console.log(`💰 最终余额：${currentBalance}`);
    console.log("=".repeat(60));
}

// 启动脚本
main().catch(e => {
    console.error("\n💥 脚本崩溃：", e.message);
    process.exit(1);
});