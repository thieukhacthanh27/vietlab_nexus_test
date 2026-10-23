const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'../vietlab_nexus_v9_1.html'),'utf8');
for(const m of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g))new vm.Script(m[1]);
const context={console,Set,Number,JSON,Date,Math,confirm:()=>true,renderAll:()=>{},showToast:()=>{},v84ResetForm:()=>{},v84AllowAction:()=>true,v84CanEditDept:()=>true,V84_DEPTS:['Phòng Hữu cơ'],V84_MATRICES:['NT'],v84View:{editCode:''},state:{equipment:[],methodRegistry:[],catalogBacklog:[],auditLogs:[],currentUser:{username:'admin'}},persistState:()=>true,addAuditEntry(){context.state.auditLogs.push({action:'test'});context.persistState();},v84Val:id=>context.values[id]||'',values:{},FileReader:class{readAsText(f){this.result=f.text;this.onload();}}};vm.createContext(context);
function load(start,end){vm.runInContext(html.slice(html.indexOf(start),html.indexOf(end,html.indexOf(start))),context);}
load('function v84Normalize(', 'function v84Audit(');
load('function v84CsvParse(', 'function v84Init(');
load('function v92MethodError(', 'function v84RenderMethods(');
load('var V84_CSV_HEADERS=', 'function v84BacklogView(');
let count=0;function ok(v,msg){assert(v,msg);count++;}
const m={dept:'Phòng Hữu cơ',matrix:'NT',methodCode:'M1',methodName:'Test',parameter:'Benzene',mdl:'0',loq:'1',lcsMin:'70',lcsMax:'130',rpdMax:'20'};
ok(context.v92MethodError(m)==='','valid zero');
for(const value of ['NaN','Infinity','-1','abc','1,2','1e999'])ok(!!context.v92MethodError({...m,mdl:value}),'reject '+value);
ok(!!context.v92MethodError({...m,mdl:'2'}),'loq order');ok(!!context.v92MethodError({...m,lcsMax:'60'}),'lcs order');ok(!!context.v92MethodError({...m,deviceCode:'unknown'}),'device');
context.values={v84MDept:m.dept,v84MMatrix:m.matrix,v84MCode:m.methodCode,v84MName:m.methodName,v84MParam:m.parameter,v84MMDL:'0',v84MLOQ:'1'};
context.v84SaveMethod();ok(context.state.methodRegistry.length===1,'save');ok(context.state.auditLogs.length===1,'audit once');context.v84SaveMethod();ok(context.state.methodRegistry.length===1,'duplicate');
context.values.v84MCode='M2';let before=JSON.stringify(context.state);context.persistState=()=>false;context.v84SaveMethod();ok(JSON.stringify(context.state)===before,'save quota rollback');context.persistState=()=>true;
context.state.methodRegistry[0].reference='SOP';context.state.methodRegistry[0].revision='2026';context.state.methodRegistry[0].verification='VER';context.state.methodRegistry[0].unit='mg/L';
before=JSON.stringify(context.state);context.persistState=()=>false;context.v84ApproveMethod(context.state.methodRegistry[0].id);ok(JSON.stringify(context.state)===before,'approval quota rollback');context.persistState=()=>true;context.v84ApproveMethod(context.state.methodRegistry[0].id);ok(context.state.methodRegistry[0].status==='Đã phê duyệt','approval');
const headers=context.V84_CSV_HEADERS.join(',');const row='Phòng Hữu cơ,M3,Test,Toluene,NT,,,,mg/L,0,1,,70,130,20';
context.v84ImportCsv({size:100,text:headers+'\n'+row+'\n'+row});ok(context.state.methodRegistry.length===2,'CSV deduplicate');
context.v84ImportCsv({size:100,text:headers+'\n'+row.replace('M3','M4').replace(',0,1,',',NaN,1,')});ok(context.state.methodRegistry.length===2,'CSV reject invalid numeric');
context.v84ImportCsv({size:100,text:headers+'\n'+Array(2001).fill(row.replace('M3','M5')).join('\n')});ok(context.state.methodRegistry.length===2,'oversized CSV no partial import');
context.persistState=()=>false;before=JSON.stringify(context.state);context.v84ImportCsv({size:100,text:headers+'\n'+row.replace('M3','M6')});ok(JSON.stringify(context.state)===before,'CSV quota rollback');
ok(context.v84CsvParse('a,b\n"x,y","z"')[1][0]==='x,y','quoted CSV');
assert.throws(()=>context.v84CsvParse('a,b\n"open'));count++;
console.log('PASS '+count+' regression assertions; all inline scripts compile.');
