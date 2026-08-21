// ==============================================
//  QQ群：755514159
// ==============================================
/************可自定义配置区************/
var token = "cc0b8c05-524c-4b13-8db1-5d1ed0e3027d";
var deviceId = "be43306f057efa77470bd35196f515647d3d7573337644f59510e1ddd889a763";
var oaid = "eaa53f5d778d8958";
var loopTimes = 100;
var eCPMmin = 40000;
var eCPMmax = 60000;
var targetBalance = 8000;
var version = "1071";
/************固定配置区************/
var apiHost = "yx1475.hengcairuanjian.cn";
var placementId = "1258967048119677";
var placementId2 = "1258967048119678";
var network_firm_id = "19";
var network_name = "Sigbom Ads";
var appname = "恒彩科技";

var userInfoApi = "https://" + apiHost + "/api/Member/Guserinfo";
var adReportApi = "https://" + apiHost + "/api/Sigbom/AOter";
var adTypeApi = "https://" + apiHost + "/api/Sigbom/ATye";

const https = require('https');
const { setTimeout: sleep } = require('timers/promises');

console.log("🚀 恒彩科技广告上报脚本开始执行 | QQ群：755514159");
console.log("📅 当前时间：" + new Date().toLocaleString());
console.log("🎯 目标余额：" + targetBalance);

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
                    "version": version,
                    ...options.headers
                },
                timeout: 10000
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
            req.on('timeout', () => { req.destroy(); reject(new Error('超时')) });
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
                    "version": version,
                    ...options.headers
                },
                timeout: 15000
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
            req.on('timeout', () => { req.destroy(); reject(new Error('超时')) });
            req.write(postData);
            req.end();
        });
    }
};

async function callATye(type) {
    try {
        const params = { ad_type: 1, type, deviceId, oaid };
        const res = await http.post(adTypeApi, params, {
            headers: { host: apiHost, token, "user-agent": "okhttp/4.10.0" }
        });
        console.log(`📡 ATye(${type}) 状态：${res.statusCode}`);
        return true;
    } catch (e) {
        console.log(`❌ ATye异常：${e.message}`);
        return false;
    }
}

async function main() {
    console.log("🔍 查询初始余额...");
    let currentBalance = 0;

    try {
        const res = await http.get(userInfoApi, {
            headers: { host: apiHost, token, "user-agent": "okhttp/4.10.0" }
        });
        const json = res.body.json();
        if (json?.data?.userinfo) {
            currentBalance = json.data.userinfo.forecast_gold || 0;
            console.log("💰 初始余额：" + currentBalance);
            if (currentBalance >= targetBalance) return console.log("✅ 已达目标");
        }
    } catch (e) {
        console.log("❌ 查询余额失败：" + e.message);
        return;
    }

    for (let o = 1; o <= loopTimes; o++) {
        console.log(`\n========= 第 ${o}/${loopTimes} 次 =========`);
        try {
            await callATye(2);
            await sleep(500);

            const loadId = genUUID();
            const eCPM = Math.round(eCPMmin + Math.random() * (eCPMmax - eCPMmin));
            const usePlacementId = Math.random() > 0.5 ? placementId : placementId2;

            const paramsObj = {
                networkPlacementId: usePlacementId,
                placementId: usePlacementId,
                networkId: network_firm_id,
                loadId,
                eCPM,
                version,
                dividends: "4",
                ad_type: "1",
                type: "2",
                deviceId,
                oaid,
                sgin: "",
                tc: ""
            };

            const res = await http.post(adReportApi, paramsObj, {
                headers: { host: apiHost, token, "user-agent": "okhttp/4.10.0" }
            });

            console.log("📥 上报状态：" + res.statusCode);
            await sleep(2000);

            const balRes = await http.get(userInfoApi, {
                headers: { host: apiHost, token, "user-agent": "okhttp/4.10.0" }
            });
            const balJson = balRes.body.json();
            if (balJson?.data?.userinfo) {
                currentBalance = balJson.data.userinfo.forecast_gold || 0;
                console.log("💰 当前余额：" + currentBalance);
                if (currentBalance >= targetBalance) {
                    console.log("🎉 已达目标，停止");
                    return;
                }
            }

        } catch (e) {
            console.log("❌ 异常：" + e.message);
            await sleep(5000);
            continue;
        }

        if (o < loopTimes) {
            const st = 28000 + Math.random() * 7000;
            console.log(`⏳ 等待 ${Math.round(st/1000)}s`);
            await sleep(st);
        }
    }

    console.log("\n🎊 任务完成");
    console.log("💰 最终余额：" + currentBalance);
}

function genUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c == 'x' ? r : (r & 3 | 8)).toString(16);
    });
}

main().catch(e => console.error("❌ 脚本崩溃：", e.message));