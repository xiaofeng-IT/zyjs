/*
    name: "随机美句"
    cron: 0 40 9 * * *
    环境变量名: MEIJU_LIST
    备注: 无需账号
*/

const { installShim } = require('../_lib/airscriptShim');
installShim({
  taskName: 'meiju', configKey: 'MEIJU_LIST',
  pushHeader: '【随机美句】', requiresAccount: false, line: 21
});

const logo = "ql_sign_script : https://github.com/unitaryhighs/ql_sign_script"
var sheetNameSubConfig = "meiju";
var pushHeader = "【随机美句】";
var sheetNameConfig = "CONFIG", sheetNamePush = "PUSH", sheetNameEmail = "EMAIL";
var flagSubConfig = 0, flagConfig = 0, flagPush = 0;
var line = 21;
var message = "", messageArray = [], messageOnlyError = 0, messageNickname = 0;
var messageHeader = [], messagePushHeader = pushHeader;
var version = 1;
var separator = "##########MOKU##########";
var jsonPush = [
  { name: "bark", key: "xxxxxx", flag: "0" },
  { name: "pushplus", key: "xxxxxx", flag: "0" },
  { name: "ServerChan", key: "xxxxxx", flag: "0" },
  { name: "email", key: "xxxxxx", flag: "0" },
  { name: "dingtalk", key: "xxxxxx", flag: "0" },
  { name: "discord", key: "xxxxxx", flag: "0" },
];
var jsonEmail = { server: "", port: "", sender: "", authorizationCode: "" };

function checkVesion(){
  try{ let t = Application.Range("A1").Text; Application.Range("A1").Value = t; version = 1; }
  catch{ version = 2; }
}
function emailConfig() {
  for (let i = 0; i < jsonPush.length; i++) {
    if (jsonPush[i].name == "email" && jsonPush[i].flag == 1) {
      let flag = ActivateSheet(sheetNameEmail);
      if (flag == 1) {
        jsonEmail.server = Application.Range("A2").Text;
        jsonEmail.port = Application.Range("B2").Text;
        jsonEmail.sender = Application.Range("C2").Text;
        jsonEmail.authorizationCode = Application.Range("D2").Text;
      }
      break;
    }
  }
}

// =================共用开始===================
  checkVesion()
  flagConfig = ActivateSheet(sheetNameConfig);
  if (flagConfig == 1) {
    for (let i = 2; i <= 100; i++) {
      let name = Application.Range("A" + i).Text;
      if (name == "") break;
      if (name == sheetNameSubConfig) {
        if (Application.Range("C" + i).Text == "是") messageOnlyError = 1;
        if (Application.Range("D" + i).Text == "是") messageNickname = 1;
        break;
      }
    }
  }
  flagPush = ActivateSheet(sheetNamePush);
  if (flagPush == 1) {
    for (let i = 2; i <= line; i++) {
      let pushName = Application.Range("A" + i).Text;
      if (pushName == "") break;
      jsonPushHandle(pushName, Application.Range("C" + i).Text, Application.Range("B" + i).Text);
    }
  }
  emailConfig();
  flagSubConfig = ActivateSheet(sheetNameSubConfig);
  if (flagSubConfig == 1) {
    if(qlSwitch != 1){
      for (let i = 2; i <= line; i++) {
        var cookie = Application.Range("A" + i).Text;
        if (cookie == "") break;
        if (Application.Range("B" + i).Text == "是") execHandle(cookie, i);
      }
      message = messageMerge()
    } else {
      for (let i = 2; i <= line; i++) {
        var cookie = Application.Range("A" + i).Text;
        if (cookie == "") break;
        if (Application.Range("B" + i).Text == "是") {
          console.log("🧑 开始执行用户：1")
          execHandle(cookie, i);
          break;
        }
      }
    }
  }

function ActivateSheet(sheetName) {
    let flag = 0;
    try { let sheet = Application.Sheets.Item(sheetName); sheet.Activate(); flag = 1; }
    catch { flag = 0; }
    return flag;
}
function jsonPushHandle(pushName, pushFlag, pushKey) {
  for (let i = 0; i < jsonPush.length; i++) {
    if (jsonPush[i].name == pushName && pushFlag == "是") { jsonPush[i].flag = 1; jsonPush[i].key = pushKey; }
  }
}
function messageMerge(){
    let msg = ""
  for(i=0; i<messageArray.length; i++){
    if(messageArray[i] != "" && messageArray[i] != null) msg += "\n" + messageHeader[i] + messageArray[i];
  }
  if(msg != "") { console.log(msg + "\n") }
  return msg
}
function sleep(d) { for (var t = Date.now(); Date.now() - t <= d; ); }
function getsign(data) {
    return Crypto.createHash("md5").update(data, "utf8").digest("hex").toString();
}
// =================共用结束===================

// 结果处理函数 - 文本直接输出
function resultHandle(resp, pos){
    posHttp += 1
    let messageSuccess = "";
    let messageFail = "";
    posLabel = pos - 2;
    messageHeader[posLabel] = ""

    let content = resp.text()
    messageSuccess += content

    flagResultFinish = 1;
    if (messageOnlyError == 1) {
      messageArray[posLabel] = messageFail;
    } else {
      messageArray[posLabel] = messageFail != "" ? messageFail + " " + messageSuccess : messageSuccess;
    }
    return flagResultFinish
}

// 执行函数
function execHandle(cookie, pos) {
    posHttp = 0
    qlpushFlag -= 1
    messageSuccess = "";
    messageFail = "";

    let url = "https://api.suyanw.cn/api/meiju"
    if(qlSwitch != 1){
      resp = HTTP.fetch(url, { method: "get", headers: {} });
      resultHandle(resp, pos)
    } else {
      option = "get"
      resp = HTTP.post(url, {}, { headers: {} }, option);
    }
}

global.resultHandle = resultHandle;
global.execHandle = execHandle;
global.messageMerge = messageMerge;
