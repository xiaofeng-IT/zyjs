/*
 * 环境变量 TGB 配置说明（支持多账号换行）：
 *   变量名：TGB
 *   格式：手机号#密码，一行一个账号
 *   示例（单账号）：
 *     TGB="13800138000#password"
 *   示例（多账号换行，使用 \n 分隔）：
 *     TGB="13800138000#password\n13900139000#password\n13700137000#password"
 *   实际在 Shell 或 Docker 中设置时，换行符可能用字面换行或 \n，本程序会自动识别。
 */

const axios = require('axios');
const UA = 'Mozilla/5.0 (Linux; Android 16; V2426A Build/BP2A.250605.031.A3_V000L1; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.135 Mobile Safari/537.36 TuiGuangBaoAndroid/1.0.2';
const BASE_PLUGIN = 'https://tg.suewammes.com/plugin.php?id=view&modac=sign';
const LOGIN_URL = 'https://tg.suewammes.com/member.php?mod=logging&action=login&loginsubmit=yes&mobile=2';

axios.defaults.timeout = 15000;

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 通用请求头
function getHeaders(cookie = '') {
    return {
        'User-Agent': UA,
        'Cookie': cookie,
        'x-requested-with': 'XMLHttpRequest',
        'Accept': '*/*',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Android WebView";v="134"',
        'sec-ch-ua-mobile': '?1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://tg.suewammes.com/plugin.php?id=xigua_hh&ac=invite'
    }
}

// 账号登录
async function loginAccount(phone, pwd) {
    try {
        console.log(`开始提交账号${phone}登录请求`);
        const formData = new URLSearchParams();
        formData.append('referer', 'https://tg.suewammes.com/plugin.php?id=xigua_hb&id=xigua_hb&needlogin=1&mobile=2');
        formData.append('fastloginfield', 'username');
        formData.append('cookietime', '2592000');
        formData.append('username', phone);
        formData.append('password', pwd);

        const loginRes = await axios({
            method: 'POST',
            url: LOGIN_URL,
            headers: {
                ...getHeaders(),
                'Content-Type': 'application/x-www-form-urlencoded',
                'origin': 'https://tg.suewammes.com',
                'upgrade-insecure-requests': '1'
            },
            data: formData.toString()
        });

        const allCookieArr = loginRes.headers['set-cookie'] || [];
        if(allCookieArr.length === 0){
            throw new Error("登录无Cookie，账号密码错误/被拦截");
        }
        const finalCookie = allCookieArr.map(item => item.split(';')[0]).join('; ');
        console.log(`✅ ${phone} 登录成功`);
        return finalCookie;
    } catch (e) {
        console.log(`❌ ${phone} 登录失败：${e.message}`);
        return null;
    }
}

// 获取会话动态formhash
async function getSessionFormhash(cookie) {
    try {
        const res = await axios.get(BASE_PLUGIN, { headers: getHeaders(cookie) });
        const reg = /formhash["']?\s*[:=]\s*["']?([0-9a-f]{8})["']?/i;
        const match = res.data.match(reg);
        if(match){
            const hash = match[1];
            console.log(`🔑 formhash: ${hash}`);
            return hash;
        }else{
            throw new Error("页面提取不到formhash");
        }
    }catch(e){
        console.log(`❌ 获取formhash失败: ${e.message}`);
        return null;
    }
}

// 查询广告任务状态
async function getTaskStatus(cookie) {
    try {
        const res = await axios({ method: 'GET', url: `${BASE_PLUGIN}&submodac=status`, headers: getHeaders(cookie) });
        if (res.data.code !== 0) throw new Error(`code:${res.data.code}`);
        return res.data.data;
    } catch (e) {
        console.log(`❌ 查询任务失败：${e.message}`);
        return null;
    }
}

// 获取广告Token
async function getNextAdToken(cookie, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=next_ad`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        if (res.data.code !== 0) throw new Error(res.data.msg || '获取广告失败');
        return res.data.data;
    } catch (e) {
        console.log(`❌ 获取广告Token失败：${e.message}`);
        return null;
    }
}

// 上报广告观看完成
async function submitAdComplete(cookie, token, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        params.append('token', token);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=complete_ad`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        if (res.data.code !== 0) throw new Error(res.data.msg || '上报失败');
        return res.data.data;
    } catch (e) {
        console.log(`❌ 广告上报失败：${e.message}`);
        return null;
    }
}

// 领取奖励
async function claimReward(cookie, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=claim`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        console.log(`🎁 领奖返回：${res.data.msg}`);
        return res.data.data;
    } catch (e) {
        console.log(`❌ 领奖失败：${e.message}`);
        return null;
    }
}

// 单账号完整流程：登录→循环刷广告领奖
async function runSingleTask(phone, pwd, idx) {
    console.log(`\n========== 账号${idx} ${phone} 开始执行 ==========`);
    const cookie = await loginAccount(phone, pwd);
    if (!cookie) return;

    while (true) {
        const taskInfo = await getTaskStatus(cookie);
        if (!taskInfo) break;
        const { viewed_count, target_count, countdown_seconds, can_claim, claimed } = taskInfo;
        console.log(`📊 广告进度：${viewed_count}/${target_count} | ✅可领奖:${can_claim} | 📅今日已领取:${claimed}`);

        if (can_claim && !claimed) {
            console.log(`🎉 广告任务已满，准备执行领奖！`);
            await delay(2000);
            const fh = await getSessionFormhash(cookie);
            if(!fh) break;
            await claimReward(cookie, fh);
            console.log(`💰 ${phone}今日奖励领取完毕，任务结束`);
            break;
        }
        if (viewed_count >= target_count) {
            console.log(`✅ ${phone}今日广告任务全部完成`);
            break;
        }
        if (countdown_seconds > 0) {
            console.log(`⏳ 冷却等待 ${countdown_seconds} 秒`);
            await delay(countdown_seconds * 1000);
        }

        const fh = await getSessionFormhash(cookie);
        if(!fh) break;

        const adData = await getNextAdToken(cookie, fh);
        if (!adData) break;
        console.log(`▶ 获取广告Token：${adData.token}，模拟观看22秒`);
        await delay(22000);

        const newTask = await submitAdComplete(cookie, adData.token, fh);
        if (!newTask) break;
        console.log(`✅ 广告上报成功，当前完成数量：${newTask.viewed_count}`);
        await delay(Math.floor(Math.random() * 3000) + 3000);
    }
}

// 程序入口
(async function main() {
    const accountEnv = process.env.TGB || '';
    if (!accountEnv.trim()) {
        console.log('❌ 请配置环境变量 TGB，格式：手机号#密码，一行一个账号');
        console.log('   单账号示例：TGB="13800138000#password"');
        console.log('   多账号换行示例：TGB="13800138000#password\\n13900139000#password\\n13700137000#password"');
        process.exit(1);
    }
    // 使用正则分割，兼容 \n 和 \r\n
    const accList = accountEnv.split(/\r?\n/).filter(i => i.trim());
    console.log(`成功加载账号总数：${accList.length}`);
    for (let i = 0; i < accList.length; i++) {
        const line = accList[i].trim();
        const [phone, pwd] = line.split('#');
        if (!phone || !pwd) {
            console.log(`❌ 账号${i+1}格式错误，正确格式：手机号#密码`);
            continue;
        }
        await runSingleTask(phone.trim(), pwd.trim(), i + 1);
        await delay(6000);
    }
    console.log('\n========== 全部账号执行结束 ==========');
})();