/*
cron: 19 *\/3 * *
考勤结果，每五天检查一次
*/
const notify = require('./sendNotify')
const axios = require('axios')
const header =  {
        'Cookie': process.env.THINVENT_COOKIE

    }
const payload = process.env.THINVENT_PAYLOAD
console.log(payload)
const _0x8255=['log','getFullYear','post','catch','getMonth','statusCode','⚠⚠本月缺勤⚠⚠'];const _0x3ef1=function(_0x82553c,_0x3ef147){_0x82553c=_0x82553c-0x0;let _0x1be9e2=_0x8255[_0x82553c];return _0x1be9e2;};const today=new Date();const currentYear=today[_0x3ef1('0x1')]();const currentMonth=today[_0x3ef1('0x4')]()+0x1;let fromattedMonth='';if(currentMonth<0xa){fromattedMonth='0'+currentMonth;}else{fromattedMonth=currentMonth;}const url='http://ehr.thinvent.com:16666/Web.HR//Mobile/Account/PostMonthAttendance?a0188=6248&yearMonth='+currentYear+'-'+fromattedMonth+'&0.27744810840809886\x20';axios[_0x3ef1('0x2')](url,payload,{'headers':header})['then'](_0x329690=>{notify['sendNotify'](_0x3ef1('0x6'),_0x329690['data'][0x6]['Svalue']);console[_0x3ef1('0x0')]('statusCode:\x20'+_0x329690[_0x3ef1('0x5')]);console[_0x3ef1('0x0')](_0x329690);})[_0x3ef1('0x3')](_0x5dcf3c=>{console['error'](_0x5dcf3c);});
