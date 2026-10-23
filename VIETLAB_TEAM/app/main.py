import hashlib
import os
import secrets
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, update, delete, func, or_, exists
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal, User, AuthSession, LoginAttempt, Method, Sample, Task, Report, Audit, now
from . import schemas as S

ph = PasswordHasher()
DUMMY_HASH = ph.hash(secrets.token_urlsafe(32))
PRODUCTION = os.getenv('APP_ENV', 'development') == 'production'
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://localhost:8000').rstrip('/')
COOKIE = 'vietlab_session'
STATIC = Path(__file__).parent / 'static'

@asynccontextmanager
async def lifespan(app):
    if PRODUCTION and (not PUBLIC_ORIGIN.startswith('https://') or engine.dialect.name != 'postgresql'):
        raise RuntimeError('Production requires HTTPS PUBLIC_ORIGIN and PostgreSQL.')
    yield

app = FastAPI(title='VIETLAB Team Pilot', version='10.1-pilot', lifespan=lifespan,
              docs_url=None if PRODUCTION else '/docs', redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(','))

@app.middleware('http')
async def security(request, call_next):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        if request.headers.get('origin') and request.headers['origin'] != PUBLIC_ORIGIN:
            return JSONResponse({'detail':'Nguồn yêu cầu không được phép.'}, status_code=403)
        if 'application/json' not in request.headers.get('content-type',''):
            return JSONResponse({'detail':'Cần nội dung JSON.'}, status_code=415)
        # Read at most 64 KiB even for chunked bodies; models are small.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse({'detail':'Yêu cầu quá lớn.'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY',
        'Referrer-Policy':'same-origin','Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    if PRODUCTION: response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

@app.exception_handler(IntegrityError)
async def conflict_handler(request, exc):
    return JSONResponse({'detail':'Mã hoặc liên kết đã tồn tại. Hãy tải lại danh sách.'}, status_code=409)

@app.exception_handler(OperationalError)
async def database_handler(request, exc):
    return JSONResponse({'detail':'Cơ sở dữ liệu đang bận hoặc không sẵn sàng. Chưa xác nhận lưu; hãy tải lại trước khi thử tiếp.'}, status_code=503)

def db_session():
    with SessionLocal() as db:
        yield db

def fail(code, message):
    raise HTTPException(code, message)

def digest(token): return hashlib.sha256(token.encode()).hexdigest()

def current(request: Request, db: Session = Depends(db_session)):
    token = request.cookies.get(COOKIE, '')
    session = db.get(AuthSession, digest(token)) if token else None
    if not session or session.expires <= int(time.time()): fail(401, 'Vui lòng đăng nhập lại.')
    user = db.get(User, session.user_id)
    if not user or not user.active: fail(401, 'Tài khoản không hoạt động.')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not secrets.compare_digest(request.headers.get('x-csrf-token',''), session.csrf):
            fail(403, 'Phiên biểu mẫu không hợp lệ. Tải lại trang.')
    request.state.auth_session = session
    return user

def role(user, *allowed):
    if user.role not in allowed: fail(403, 'Vai trò không có quyền thực hiện.')

def department(user, dept):
    if user.role not in ('admin','qa','director','intake') and user.dept != dept:
        fail(403, 'Không thuộc phòng được phân quyền.')

def get(db, model, identifier):
    item = db.get(model, identifier)
    if not item: fail(404, 'Không tìm thấy hồ sơ.')
    return item

def public_user(u):
    return {k:getattr(u,k) for k in ('id','username','full_name','role','dept','active','version')}

def record(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

def audit(db, actor, action, entity, identifier, reason, before=None, after=None):
    db.add(Audit(actor_id=actor.id if actor else None, action=action, entity=entity,
                 entity_id=str(identifier), reason=reason, before=before or {}, after=after or {}))

def cas(db, obj, expected, values):
    """Compare-and-swap inside the same transaction as business changes and audit."""
    model = type(obj)
    result = db.execute(update(model).where(model.id==obj.id, model.version==expected).values(**values, version=expected+1), execution_options={'synchronize_session':False})
    if result.rowcount != 1: fail(409, 'Hồ sơ đã được người khác cập nhật. Tải lại trước khi sửa.')
    db.refresh(obj)

def lock_sample(db, sample, expected):
    if sample.status in ('released','cancelled'): fail(409, 'Mẫu đã phát hành hoặc đã hủy; không được sửa.')
    cas(db, sample, expected, {})

def task_scope(user):
    if user.role in ('admin','qa','director','intake'): return True
    if user.role == 'analyst': return (Task.assignee_id==user.id) & (Task.dept==user.dept)
    return Task.dept==user.dept

def sample_scope(user):
    if user.role in ('admin','qa','director','intake'): return True
    return exists(select(Task.id).where(Task.sample_id==Sample.id, task_scope(user)))

def task_access(user, task):
    department(user, task.dept)
    if user.role == 'analyst' and task.assignee_id != user.id: fail(403, 'Chỉ được xem công việc đã giao.')

def sample_view(sample, user):
    out = record(sample)
    if user.role in ('analyst','head'):
        out.pop('customer'); out.pop('contract')
    return out

@app.get('/')
def index(): return FileResponse(STATIC/'index.html')

@app.get('/health')
def health(db: Session = Depends(db_session)):
    db.execute(select(1))
    return {'status':'ok','version':'10.1-pilot'}

@app.post('/api/login')
def login(body:S.Login, request:Request, response:Response, db:Session=Depends(db_session)):
    timestamp=int(time.time()); ip=request.client.host if request.client else 'unknown'
    # DB-backed limiter shared by workers; gateway should add an IP rate limit.
    count=db.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.created>timestamp-900, or_(LoginAttempt.username==body.username,LoginAttempt.ip==ip)))
    if count >= 20: fail(429,'Quá nhiều lần đăng nhập thất bại. Thử lại sau 15 phút.')
    user=db.scalar(select(User).where(User.username==body.username))
    try: valid=ph.verify(user.password_hash if user else DUMMY_HASH,body.password)
    except (VerificationError,InvalidHashError): valid=False
    if not valid or not user or not user.active:
        db.add(LoginAttempt(username=body.username,ip=ip,created=timestamp));db.commit()
        fail(401,'Tên đăng nhập hoặc mật khẩu không đúng.')
    db.execute(delete(AuthSession).where(AuthSession.expires<timestamp))
    db.execute(delete(LoginAttempt).where(LoginAttempt.created<timestamp-86400))
    token=secrets.token_urlsafe(48); csrf=secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=digest(token),user_id=user.id,csrf=csrf,expires=timestamp+8*3600))
    audit(db,user,'login','user',user.id,'Đăng nhập thành công');db.commit()
    response.set_cookie(COOKIE,token,httponly=True,secure=PRODUCTION,samesite='strict',max_age=8*3600,path='/')
    return {'user':public_user(user),'csrf':csrf}

@app.get('/api/me')
def me(request:Request,user:User=Depends(current)):
    return {'user':public_user(user),'csrf':request.state.auth_session.csrf}

@app.post('/api/logout')
def logout(request:Request,response:Response,user:User=Depends(current),db:Session=Depends(db_session)):
    db.delete(request.state.auth_session);audit(db,user,'logout','user',user.id,'Đăng xuất');db.commit()
    response.delete_cookie(COOKIE,path='/');return {'ok':True}

@app.post('/api/password')
def password(body:S.ChangePassword,user:User=Depends(current),db:Session=Depends(db_session)):
    try: valid=ph.verify(user.password_hash,body.old_password)
    except VerificationError: valid=False
    if not valid: fail(400,'Mật khẩu hiện tại không đúng.')
    user.password_hash=ph.hash(body.new_password)
    db.execute(delete(AuthSession).where(AuthSession.user_id==user.id))
    audit(db,user,'password_changed','user',user.id,'Đổi mật khẩu; thu hồi toàn bộ phiên');db.commit()
    return {'ok':True}

@app.get('/api/users')
def users(user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'admin','head','intake','qa')
    stmt=select(User).order_by(User.full_name)
    if user.role=='head': stmt=stmt.where(User.dept==user.dept,User.active==True)
    if user.role in ('intake','qa'): stmt=stmt.where(User.active==True)
    rows=db.scalars(stmt.limit(500)).all()
    if user.role=='admin': return [public_user(u) for u in rows]
    return [{k:getattr(u,k) for k in ('id','full_name','role','dept')} for u in rows]

@app.post('/api/users',status_code=201)
def new_user(body:S.NewUser,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'admin')
    obj=User(**body.model_dump(exclude={'password'}),password_hash=ph.hash(body.password))
    db.add(obj);db.flush();audit(db,user,'create','user',obj.id,'Tạo tài khoản',after=public_user(obj));db.commit()
    return public_user(obj)

@app.post('/api/users/{identifier}/active')
def active_user(identifier:int,body:S.SetActive,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'admin');target=get(db,User,identifier)
    if target.id==user.id: fail(400,'Không tự khóa tài khoản đang thao tác.')
    before=public_user(target);cas(db,target,body.version,{'active':body.active})
    db.execute(delete(AuthSession).where(AuthSession.user_id==target.id))
    audit(db,user,'set_active','user',target.id,body.reason,before,public_user(target));db.commit()
    return public_user(target)

@app.get('/api/methods')
def methods(q:str=Query('',max_length=100),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user:User=Depends(current),db:Session=Depends(db_session)):
    stmt=select(Method)
    if user.role in ('analyst','head'): stmt=stmt.where(Method.dept==user.dept)
    if q: stmt=stmt.where(or_(Method.code.icontains(q,autoescape=True),Method.parameter.icontains(q,autoescape=True)))
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    return {'total':total,'items':[record(x) for x in db.scalars(stmt.order_by(Method.id.desc()).offset(offset).limit(limit))]}

@app.post('/api/methods',status_code=201)
def new_method(body:S.NewMethod,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'head','analyst');department(user,body.dept)
    obj=Method(**body.model_dump(),author_id=user.id);db.add(obj);db.flush()
    audit(db,user,'create','method',obj.id,'Tạo phiên bản Method chờ duyệt',after=record(obj));db.commit();return record(obj)

@app.post('/api/methods/{identifier}/approve')
def approve_method(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'head');obj=get(db,Method,identifier);department(user,obj.dept)
    if obj.author_id==user.id: fail(403,'Người soạn không tự phê duyệt Method.')
    if obj.status!='draft': fail(409,'Method đã được duyệt.')
    before=record(obj);cas(db,obj,body.version,{'status':'approved','approver_id':user.id,'approved_at':now()})
    audit(db,user,'approve','method',obj.id,body.reason,before,record(obj));db.commit();return record(obj)

@app.get('/api/samples')
def samples(q:str=Query('',max_length=100),status:str=Query('',max_length=30),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user:User=Depends(current),db:Session=Depends(db_session)):
    stmt=select(Sample).where(sample_scope(user))
    if q: stmt=stmt.where(Sample.code.icontains(q,autoescape=True))
    if status: stmt=stmt.where(Sample.status==status)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    items=[sample_view(x,user) for x in db.scalars(stmt.order_by(Sample.id.desc()).offset(offset).limit(limit))]
    return {'total':total,'items':items}

@app.post('/api/samples',status_code=201)
def new_sample(body:S.NewSample,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'intake')
    if body.due < body.collected_at.date(): fail(422,'Hạn trả không được trước ngày lấy mẫu.')
    obj=Sample(**body.model_dump(mode='json'));db.add(obj);db.flush()
    audit(db,user,'receive','sample',obj.id,'Tiếp nhận: '+body.condition,after=record(obj));db.commit();return sample_view(obj,user)

@app.get('/api/samples/{identifier}')
def sample_detail(identifier:int,user:User=Depends(current),db:Session=Depends(db_session)):
    obj=db.scalar(select(Sample).where(Sample.id==identifier,sample_scope(user)))
    if not obj: fail(404,'Không tìm thấy mẫu trong phạm vi quyền.')
    items=db.scalars(select(Task).where(Task.sample_id==identifier,task_scope(user)).order_by(Task.id)).all()
    result=sample_view(obj,user);result['tasks']=task_views(db,items)
    rep=db.scalar(select(Report).where(Report.sample_id==identifier))
    result['report_id']=rep.id if rep and user.role in ('admin','intake','qa','director') else None
    return result

def task_views(db, tasks):
    if not tasks: return []
    methods={m.id:m for m in db.scalars(select(Method).where(Method.id.in_({t.method_id for t in tasks})))}
    users={u.id:u for u in db.scalars(select(User).where(User.id.in_({t.assignee_id for t in tasks})))}
    out=[]
    for t in tasks:
        data=record(t);m=methods[t.method_id]
        data['method']={k:getattr(m,k) for k in ('code','parameter','unit','revision','matrix')}
        data['assignee']=users[t.assignee_id].full_name;out.append(data)
    return out

def task_view(db,t):
    return task_views(db,[t])[0]

@app.post('/api/samples/{identifier}/assign',status_code=201)
def assign(identifier:int,body:S.Assign,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'intake','head');sample=get(db,Sample,identifier);method=db.scalar(select(Method).where(Method.id==body.method_id).with_for_update());person=get(db,User,body.assignee_id)
    if not method: fail(404,'Không tìm thấy Method.')
    department(user,method.dept)
    if user.role=='head' and not db.scalar(select(Sample.id).where(Sample.id==identifier,sample_scope(user))):
        fail(404,'Mẫu chưa được phân công tới phòng.')
    if method.status!='approved' or method.matrix!=sample.matrix: fail(422,'Method phải được duyệt và đúng nền mẫu.')
    if person.role!='analyst' or person.dept!=method.dept or not person.active: fail(422,'Cần nhân viên phân tích đang hoạt động thuộc đúng phòng.')
    lock_sample(db,sample,body.version)
    if db.scalar(select(func.count()).select_from(Task).where(Task.sample_id==identifier))>=200:
        fail(422,'Tối đa 200 chỉ tiêu mỗi mẫu trong bản pilot.')
    task=Task(sample_id=sample.id,method_id=method.id,dept=method.dept,assignee_id=person.id)
    db.add(task);sample.status='working';db.flush()
    audit(db,user,'assign','task',task.id,body.reason,after=record(task));db.commit();return task_view(db,task)

@app.post('/api/tasks/{identifier}/result')
def save_result(identifier:int,body:S.Result,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'analyst');task=get(db,Task,identifier);task_access(user,task)
    if task.status!='draft': fail(409,'Kết quả đã gửi duyệt; cần trả lại trước khi sửa.')
    sample=get(db,Sample,task.sample_id);lock_sample(db,sample,sample.version)
    before=record(task);cas(db,task,body.version,{**body.model_dump(exclude={'version','reason'}),'author_id':user.id,'updated_at':now()})
    audit(db,user,'save_result','task',task.id,body.reason,before,record(task));db.commit();return task_view(db,task)

@app.post('/api/tasks/{identifier}/submit')
def submit(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'analyst');task=get(db,Task,identifier);task_access(user,task)
    if task.author_id!=user.id: fail(422,'Cần tự kiểm tra và lưu lại kết quả sau khi nhận phân công.')
    if task.status!='draft' or not task.value or not task.qc_pass or not task.evidence_ref or not task.qc_note:
        fail(422,'Cần kết quả nháp, QC đạt và tham chiếu hồ sơ gốc trước khi gửi.')
    sample=get(db,Sample,task.sample_id);lock_sample(db,sample,sample.version)
    before=record(task);cas(db,task,body.version,{'status':'submitted','updated_at':now()})
    audit(db,user,'submit','task',task.id,body.reason,before,record(task));db.commit();return task_view(db,task)

@app.post('/api/tasks/{identifier}/review')
def review(identifier:int,body:S.Review,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'head');task=get(db,Task,identifier);department(user,task.dept)
    if task.author_id==user.id: fail(403,'Không được tự duyệt kết quả của mình.')
    if task.status!='submitted': fail(409,'Kết quả chưa ở trạng thái chờ duyệt.')
    sample=get(db,Sample,task.sample_id);lock_sample(db,sample,sample.version)
    before=record(task);approved=body.decision=='approve'
    cas(db,task,body.version,{'status':'reviewed' if approved else 'draft','reviewer_id':user.id if approved else None,'reviewed_at':now() if approved else None,'updated_at':now()})
    audit(db,user,'review_'+body.decision,'task',task.id,body.reason,before,record(task));db.commit();return task_view(db,task)

@app.post('/api/samples/{identifier}/return')
def return_sample(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'qa');sample=get(db,Sample,identifier);lock_sample(db,sample,body.version)
    tasks=db.scalars(select(Task).where(Task.sample_id==identifier)).all()
    if not tasks: fail(422,'Mẫu chưa có chỉ tiêu.')
    for task in tasks:
        before=record(task);cas(db,task,task.version,{'status':'draft','reviewer_id':None,'reviewed_at':None,'updated_at':now()})
        audit(db,user,'qa_return','task',task.id,body.reason,before,record(task))
    db.commit();return {'ok':True}

@app.post('/api/samples/{identifier}/release',status_code=201)
def release(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'qa');sample=get(db,Sample,identifier);lock_sample(db,sample,body.version)
    tasks=db.scalars(select(Task).where(Task.sample_id==identifier).order_by(Task.id)).all()
    if not tasks or any(t.status!='reviewed' or not t.qc_pass for t in tasks): fail(422,'Tất cả chỉ tiêu phải được trưởng phòng duyệt và QC đạt.')
    if any(user.id in (t.author_id,t.reviewer_id) for t in tasks): fail(403,'Người phát hành phải độc lập với người nhập và duyệt kết quả.')
    before=record(sample);sample.status='released'
    snapshot={'sample':record(sample),'results':task_views(db,tasks), 'release_note':body.reason,
              'issuer':public_user(user),'label':'PHIẾU KẾT QUẢ NỘI BỘ — BẢN THỬ NGHIỆM, KHÔNG PHẢI CoA CHÍNH THỨC'}
    obj=Report(id=str(uuid.uuid4()),sample_id=sample.id,issued_by=user.id,snapshot=snapshot)
    db.add(obj);db.flush();audit(db,user,'release','sample',sample.id,body.reason,before,{'report_id':obj.id,'status':'released'});db.commit()
    return {'report_id':obj.id,'issued_at':obj.issued_at}

@app.get('/api/reports/{identifier}')
def report(identifier:str,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'qa','intake','director','admin');return record(get(db,Report,identifier))

@app.get('/api/audit')
def logs(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'qa','director','admin')
    return {'total':db.scalar(select(func.count()).select_from(Audit)), 'items':[record(x) for x in db.scalars(select(Audit).order_by(Audit.id.desc()).offset(offset).limit(limit))]}

@app.get('/api/dashboard')
def dashboard(user:User=Depends(current),db:Session=Depends(db_session)):
    scoped=select(Sample).where(sample_scope(user))
    grouped=db.execute(select(Sample.status,func.count()).where(sample_scope(user)).group_by(Sample.status)).all()
    pending=db.scalar(select(func.count()).select_from(Task).join(Sample,Task.sample_id==Sample.id).where(task_scope(user),Task.status=='submitted',Sample.status.not_in(['cancelled','released'])))
    overdue=db.scalar(select(func.count()).select_from(Sample).where(sample_scope(user),Sample.status.not_in(['released','cancelled']),Sample.due<datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()))
    return {'counts':dict(grouped),'pending_review':pending,'overdue':overdue,'scope':'Công việc được giao' if user.role=='analyst' else ('Phòng '+user.dept if user.role=='head' else 'Toàn công ty')}


@app.post('/api/methods/{identifier}/retire')
def retire_method(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'head');obj=get(db,Method,identifier);department(user,obj.dept)
    if obj.status!='approved': fail(409,'Chỉ ngừng sử dụng Method đang được duyệt.')
    before=record(obj);cas(db,obj,body.version,{'status':'retired'})
    audit(db,user,'retire','method',obj.id,body.reason,before,record(obj));db.commit();return record(obj)

@app.post('/api/samples/{identifier}/edit')
def edit_sample(identifier:int,body:S.EditSample,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'intake');sample=get(db,Sample,identifier)
    if body.code!=sample.code: fail(422,'Không đổi mã mẫu đã cấp. Hãy hủy hồ sơ nhập nhầm và tạo mới.')
    if body.due<body.collected_at.date(): fail(422,'Hạn trả không được trước ngày lấy mẫu.')
    before=record(sample);lock_sample(db,sample,body.version)
    tasks=db.scalars(select(Task).where(Task.sample_id==identifier)).all()
    if any(t.status!='draft' for t in tasks): fail(409,'Cần KCS trả kết quả về nháp trước khi sửa hồ sơ mẫu.')
    if tasks and body.matrix!=sample.matrix: fail(422,'Không đổi nền mẫu khi đã phân công chỉ tiêu.')
    values=body.model_dump(mode='json',exclude={'version','reason','code'})
    if all(getattr(sample,k)==v for k,v in values.items()): fail(422,'Chưa có thông tin thay đổi.')
    scientific=any(getattr(sample,k)!=values[k] for k in ('location','condition','collected_at'))
    for k,v in values.items(): setattr(sample,k,v)
    if scientific:
        for task in tasks:
            old=record(task);cas(db,task,task.version,{'qc_pass':False,'updated_at':now()})
            audit(db,user,'sample_context_changed','task',task.id,body.reason,old,record(task))
    audit(db,user,'edit','sample',sample.id,body.reason,before,record(sample));db.commit();return sample_view(sample,user)

@app.post('/api/samples/{identifier}/cancel')
def cancel_sample(identifier:int,body:S.Version,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'intake','qa');sample=get(db,Sample,identifier);before=record(sample)
    lock_sample(db,sample,body.version)
    if user.role=='intake' and db.scalar(select(func.count()).select_from(Task).where(Task.sample_id==identifier)):
        fail(403,'Mẫu đã phân công: cần KCS hủy sau khi đánh giá ảnh hưởng.')
    sample.status='cancelled'
    audit(db,user,'cancel','sample',sample.id,body.reason,before,record(sample));db.commit();return sample_view(sample,user)

@app.post('/api/tasks/{identifier}/reassign')
def reassign(identifier:int,body:S.Reassign,user:User=Depends(current),db:Session=Depends(db_session)):
    role(user,'head','intake');task=get(db,Task,identifier);department(user,task.dept)
    if task.status!='draft': fail(409,'Chỉ chuyển người phụ trách khi kết quả ở bản nháp.')
    if task.assignee_id==body.assignee_id: fail(422,'Người phụ trách không thay đổi.')
    person=get(db,User,body.assignee_id)
    if not person.active or person.role!='analyst' or person.dept!=task.dept:
        fail(422,'Cần nhân viên phân tích hoạt động thuộc đúng phòng.')
    sample=get(db,Sample,task.sample_id);lock_sample(db,sample,sample.version)
    before=record(task);cas(db,task,body.version,{'assignee_id':person.id,'qc_pass':False,'updated_at':now()})
    audit(db,user,'reassign','task',task.id,body.reason,before,record(task));db.commit();return task_view(db,task)

app.mount('/static',StaticFiles(directory=STATIC),name='static')
