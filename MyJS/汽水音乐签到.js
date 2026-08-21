//new Env("汽水音乐签到")
/*
汽水音乐自动签到脚本 - 青龙面板版本
版本: v1.0
功能: 签到、看广告、做任务、防封

========================= 使用说明 =========================

【第一步】抓包获取Cookie
1. 手机打开HttpCanary抓包工具
2. 打开汽水音乐APP，登录账号
3. 停止抓包，搜索关键词 "sessionid" 或 "cookie"
4. 找到类似这样的值:
   sessionid=xxxxx; uid_tt=xxxxx; sid_tt=xxxxx
5. 复制完整的Cookie字符串

【第二步】青龙面板添加环境变量
1. 登录青龙面板
2. 左侧菜单: 环境变量
3. 新建变量:
   - 变量名: QS_COOKIE
   - 变量值: 你抓包获取的Cookie
4. 支持多账号，用 @@@ 分隔

【第三步】创建定时任务
1. 左侧菜单: 定时任务
2. 新建任务:
   - 名称: 汽水音乐自动任务
   - 命令: task qishui_sign.js
   - 定时: 0 0-23/6 * * * (每6小时)
   - 脚本类型: Nodejs

============================================================
*/

const https = require('https');
const http = require('http');
const crypto = require('crypto');

// ==================== 配置 ====================
const COOKIE_VAR = process.env.QS_COOKIE || '';
const API_BASE = 'https://api-ss.feishu.cn';
const APP_VERSION = '3.0.0';

// 防封配置
const DELAY_MIN = 2000;  // 最小延迟(ms)
const DELAY_MAX = 5000;  // 最大延迟(ms)
const RETRY_TIMES = 3;

// ==================== 工具函数 ====================
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function randomDelay() {
    const t = Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1)) + DELAY_MIN;
    return delay(t);
}

function getTimestamp() {
    return Date.now().toString();
}

function md5(str) {
    return crypto.createHash('md5').update(str).digest('hex');
}

function generateDeviceId() {
    return md5(getTimestamp() + Math.random().toString()).substring(0, 16);
}

// ==================== HTTP请求 ====================
function httpRequest(url, method, headers, data) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = url.startsWith('https');
        const client = isHttps ? https : http;
        
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port || (isHttps ? 443 : 80),
            path: urlObj.pathname + urlObj.search,
            method: method,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12; OnePlus ACE5 Build/SKQ1.211217.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.5304.105 Mobile Safari/537.36 Ssrunner/1.0 ByteEngine/3.4.8.2 AppVersion/3.0.0.4 NetType/WIFI Robinson/1.0 Locale/zh-CN',
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://ss.feishu.cn/',
                'Origin': 'https://ss.feishu.cn',
                ...headers
            }
        };
        
        const req = client.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch (e) {
                    resolve({ raw: body });
                }
            });
        });
        
        req.on('error', reject);
        req.setTimeout(10000, () => reject(new Error('Request timeout')));
        
        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

// ==================== Cookie解析 ====================
function parseCookies(cookieStr) {
    if (!cookieStr) return [];
    return cookieStr.split('@@@').map(c => c.trim()).filter(c => c.length > 0);
}

function buildHeaders(cookie) {
    return {
        'Cookie': cookie,
        'X-SS-TC': '0',
        'X-Tim': getTimestamp(),
        'X-Device-Id': generateDeviceId()
    };
}

// ==================== 核心功能 ====================

// 获取用户信息
async function getUserInfo(cookie) {
    console.log('[📱] 获取用户信息...');
    try {
        const headers = buildHeaders(cookie);
        const data = await httpRequest(
            `${API_BASE}/api/user/info`,
            'GET',
            headers
        );
        
        if (data.status === 0) {
            const user = data.data || {};
            console.log(`    👤 用户: ${user.username || '未知'}`);
            console.log(`    💰 金币: ${user.coins || 0}`);
            console.log(`    ⭐ 等级: Lv${user.level || 0}`);
            return user;
        } else {
            console.log(`    ⚠️ 获取失败: ${data.message || '未知错误'}`);
            return null;
        }
    } catch (e) {
        console.log(`    ❌ 异常: ${e.message}`);
        return null;
    }
}

// 检查签到状态
async function checkSignStatus(cookie) {
    console.log('[📝] 检查签到状态...');
    try {
        const headers = buildHeaders(cookie);
        const data = await httpRequest(
            `${API_BASE}/api/sign/status`,
            'GET',
            headers
        );
        
        if (data.status === 0) {
            const signed = data.data?.signed_today;
            console.log(`    ${signed ? '✅' : '⭕'} 今日${signed ? '已签到' : '未签到'}`);
            return signed;
        }
        return false;
    } catch (e) {
        console.log(`    ⚠️ 检查异常: ${e.message}`);
        return false;
    }
}

// 签到
async function signIn(cookie) {
    console.log('[🎁] 执行签到...');
    try {
        const headers = buildHeaders(cookie);
        const postData = {
            timestamp: getTimestamp(),
            device_id: generateDeviceId()
        };
        
        const data = await httpRequest(
            `${API_BASE}/api/sign/signin`,
            'POST',
            headers,
            postData
        );
        
        if (data.status === 0) {
            const coins = data.data?.coins || 0;
            console.log(`    ✅ 签到成功! +${coins}金币`);
            return true;
        } else {
            console.log(`    ❌ 签到失败: ${data.message || '未知错误'}`);
            return false;
        }
    } catch (e) {
        console.log(`    ❌ 签到异常: ${e.message}`);
        return false;
    }
}

// 看广告
async function watchAds(cookie) {
    console.log('[📺] 观看广告...');
    
    const adList = [
        { id: 'ad_video_01', name: '广告视频1' },
        { id: 'ad_video_02', name: '广告视频2' },
        { id: 'ad_video_03', name: '广告视频3' },
        { id: 'ad_splash_01', name: '开屏广告1' },
        { id: 'ad_splash_02', name: '开屏广告2' },
        { id: 'ad_reward_01', name: '激励视频1' }
    ];
    
    let successCount = 0;
    
    for (const ad of adList) {
        console.log(`    ▶️ 观看: ${ad.name}...`);
        try {
            const headers = buildHeaders(cookie);
            const postData = {
                ad_id: ad.id,
                timestamp: getTimestamp(),
                duration: Math.floor(Math.random() * 10) + 25
            };
            
            await randomDelay();
            
            const data = await httpRequest(
                `${API_BASE}/api/ad/reward`,
                'POST',
                headers,
                postData
            );
            
            if (data.status === 0) {
                const coins = data.data?.coins || 0;
                console.log(`       ✅ 完成! +${coins}金币`);
                successCount++;
            } else {
                console.log(`       ⚠️ ${data.message || '已完成或不可用'}`);
            }
        } catch (e) {
            console.log(`       ❌ 异常: ${e.message}`);
        }
        
        await randomDelay();
    }
    
    console.log(`    📊 广告完成: ${successCount}/${adList.length}`);
    return successCount;
}

// 做任务
async function doTasks(cookie) {
    console.log('[📋] 执行任务...');
    
    const tasks = [
        { api: '/api/task/listen', name: '听歌任务', coins: 20 },
        { api: '/api/task/share', name: '分享任务', coins: 10 },
        { api: '/api/task/favorite', name: '收藏任务', coins: 5 },
        { api: '/api/task/comment', name: '评论任务', coins: 8 },
        { api: '/api/task/daily', name: '日常任务', coins: 15 }
    ];
    
    let totalCoins = 0;
    
    for (const task of tasks) {
        try {
            const headers = buildHeaders(cookie);
            const postData = {
                timestamp: getTimestamp(),
                device_id: generateDeviceId()
            };
            
            await randomDelay();
            
            const data = await httpRequest(
                `${API_BASE}${task.api}`,
                'POST',
                headers,
                postData
            );
            
            if (data.status === 0) {
                const coins = data.data?.coins || task.coins;
                totalCoins += coins;
                console.log(`    ✅ ${task.name}: +${coins}金币`);
            } else {
                console.log(`    ⏭️ ${task.name}: ${data.message || '已完成'}`);
            }
        } catch (e) {
            console.log(`    ❌ ${task.name}异常: ${e.message}`);
        }
    }
    
    console.log(`    📊 任务收益: +${totalCoins}金币`);
    return totalCoins;
}

// 获取金币明细
async function getCoinDetail(cookie) {
    console.log('[💰] 获取金币明细...');
    try {
        const headers = buildHeaders(cookie);
        const data = await httpRequest(
            `${API_BASE}/api/coin/detail`,
            'GET',
            headers
        );
        
        if (data.status === 0) {
            const detail = data.data || {};
            console.log(`    今日收益: ${detail.today || 0}`);
            console.log(`    本周收益: ${detail.week || 0}`);
            console.log(`    总金币: ${detail.total || 0}`);
            return detail;
        }
        return null;
    } catch (e) {
        console.log(`    ⚠️ 获取异常: ${e.message}`);
        return null;
    }
}

// ==================== 主函数 ====================
async function main() {
    console.log('\n========================================');
    console.log('   🎵 汽水音乐自动任务脚本 v1.0');
    console.log('========================================\n');
    console.log(`⏰ 执行时间: ${new Date().toLocaleString('zh-CN')}\n`);
    
    const cookies = parseCookies(COOKIE_VAR);
    
    if (cookies.length === 0) {
        console.log('❌ 错误: 未找到 QS_COOKIE 环境变量!');
        console.log('\n请在青龙面板添加环境变量:');
        console.log('  变量名: QS_COOKIE');
        console.log('  变量值: 抓包获取的Cookie');
        console.log('  多账号: 用 @@@ 分隔');
        console.log('\n========================================\n');
        return;
    }
    
    console.log(`📱 检测到 ${cookies.length} 个账号\n`);
    
    let totalCoins = 0;
    
    for (let i = 0; i < cookies.length; i++) {
        if (cookies.length > 1) {
            console.log(`\n========== 账号 ${i + 1}/${cookies.length} ==========\n`);
        }
        
        const cookie = cookies[i];
        
        await getUserInfo(cookie);
        await randomDelay();
        
        const signed = await checkSignStatus(cookie);
        await randomDelay();
        
        if (!signed) {
            await signIn(cookie);
        } else {
            console.log('[⏭️] 跳过签到（今日已签到）');
        }
        await randomDelay();
        
        await watchAds(cookie);
        await randomDelay();
        
        const taskCoins = await doTasks(cookie);
        totalCoins += taskCoins;
        await randomDelay();
        
        await getCoinDetail(cookie);
    }
    
    console.log('\n========================================');
    console.log('   🎉 任务执行完成!');
    console.log('========================================');
    console.log(`\n📊 本次运行获得金币: ~${totalCoins}`);
    console.log('\n💡 定时任务建议:');
    console.log('   格式: 0 0-23/6 * * *');
    console.log('   说明: 每6小时执行一次');
    console.log('   时间: 0:00, 6:00, 12:00, 18:00');
    console.log('\n========================================\n');
}

main().catch(console.error);
