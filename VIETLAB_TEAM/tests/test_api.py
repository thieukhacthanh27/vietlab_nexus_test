import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(prefix='vietlab-test-',suffix='.db')
os.environ['APP_ENV']='development'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app, ph
from app.db import Base, engine, SessionLocal, User, Task, Sample, Audit, Report, AuthSession

PASSWORD='Temporary-test-only-2026!'
HASH=ph.hash(PASSWORD)
NAMES=[('admin','admin','Điều hành'),('intake','intake','Điều hành'),('analyst','analyst','Hữu cơ'),('other','analyst','Kim loại'),('peer','analyst','Hữu cơ'),('head','head','Hữu cơ'),('quality','qa','Điều hành'),('director','director','Điều hành')]

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for username,role,dept in NAMES: db.add(User(username=username,full_name=username,role=role,dept=dept,password_hash=HASH))
        db.commit()
    yield

class Client:
    def __init__(self,name):
        self.name=name;self.http=TestClient(app)
        r=self.http.post('/api/login',json={'username':name,'password':PASSWORD});assert r.status_code==200,r.text
        self.me=r.json()['user'];self.csrf=r.json()['csrf']
    def get(self,path):return self.http.get('/api'+path)
    def post(self,path,data):return self.http.post('/api'+path,json=data,headers={'x-csrf-token':self.csrf})

def success(response,expected=200):
    assert response.status_code==expected,response.text
    return response.json()

METHOD={'code':'GCMS-VOC','parameter':'Benzene','matrix':'NT','dept':'Hữu cơ','revision':'2026-01','unit':'µg/L','sop':'SOP-001','verification':'VER-001'}
SAMPLE={'code':'NT.2026-001','customer':'Khách thử nghiệm','contract':'HD-001','matrix':'NT','location':'Vị trí thử nghiệm','collected_at':'2026-01-01T08:00:00+07:00','due':'2026-12-01','condition':'Đủ chai và bảo quản đạt'}
RESULT={'value':'0.12','qc_pass':True,'qc_note':'Mẻ QC-001 đạt','evidence_ref':'NAS/2026/GCMS-001','reason':'Nhập kết quả cuối theo hồ sơ gốc'}

def fixture_work():
    a,h,i,q=Client('analyst'),Client('head'),Client('intake'),Client('quality')
    m=success(a.post('/methods',METHOD),201)
    success(h.post(f"/methods/{m['id']}/approve",{'version':m['version'],'reason':'Đã thẩm tra hồ sơ'}))
    s=success(i.post('/samples',SAMPLE),201)
    t=success(i.post(f"/samples/{s['id']}/assign",{'version':s['version'],'method_id':m['id'],'assignee_id':a.me['id'],'reason':'Phân công theo năng lực'}),201)
    return a,h,i,q,s,t

def reviewed():
    a,h,i,q,s,t=fixture_work()
    t=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':t['version']}))
    t=success(a.post(f"/tasks/{t['id']}/submit",{'version':t['version'],'reason':'Đã kiểm tra QC và hồ sơ'}))
    t=success(h.post(f"/tasks/{t['id']}/review",{'version':t['version'],'decision':'approve','reason':'Kết quả phù hợp hồ sơ gốc'}))
    return a,h,i,q,s,t

def test_full_workflow_immutable_report():
    a,h,i,q,s,t=reviewed()
    s=success(q.get(f"/samples/{s['id']}"))
    r=success(q.post(f"/samples/{s['id']}/release",{'version':s['version'],'reason':'Đã kiểm tra đầy đủ trước phát hành'}),201)
    report=success(i.get('/reports/'+r['report_id']))
    assert report['snapshot']['results'][0]['value']=='0.12'
    assert report['snapshot']['results'][0]['method']['revision']=='2026-01'
    assert a.get('/reports/'+r['report_id']).status_code==403
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':t['version']}).status_code==409
    assert q.post(f"/samples/{s['id']}/return",{'version':s['version']+1,'reason':'Thử sửa phiếu đã phát hành'}).status_code==409
    with SessionLocal() as db:
        actions=set(db.scalars(select(Audit.action)))
        assert {'receive','assign','save_result','submit','review_approve','release'}<=actions
        assert db.scalar(select(func.count()).select_from(Report))==1

def test_private_scope_and_customer_redaction():
    a,h,i,q,s,t=fixture_work();other=Client('other');peer=Client('peer')
    assert success(other.get('/samples'))['total']==0
    assert other.get(f"/samples/{s['id']}").status_code==404
    assert peer.get(f"/samples/{s['id']}").status_code==404
    assert 'customer' not in success(a.get(f"/samples/{s['id']}"))
    assert other.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}).status_code==403
    assert a.get('/audit').status_code==403
    assert a.get('/users').status_code==403

def test_no_self_approval_or_admin_business_override():
    h=Client('head');m=success(h.post('/methods',METHOD),201)
    assert h.post(f"/methods/{m['id']}/approve",{'version':1,'reason':'Tự phê duyệt không hợp lệ'}).status_code==403
    admin=Client('admin')
    assert admin.post('/samples',SAMPLE).status_code==403
    assert admin.post(f"/methods/{m['id']}/approve",{'version':1,'reason':'Quản trị không phải trưởng phòng'}).status_code==403

def test_stale_writes_do_not_overwrite_or_create_audit():
    a,h,i,q,s,t=fixture_work()
    first=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}))
    with SessionLocal() as db: before=db.scalar(select(func.count()).select_from(Audit))
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'value':'99','version':1}).status_code==409
    with SessionLocal() as db:
        assert db.get(Task,t['id']).value=='0.12'
        assert db.scalar(select(func.count()).select_from(Audit))==before
        assert db.get(Task,t['id']).version==first['version']

def test_two_simultaneous_writers_only_one_wins():
    a,h,i,q,s,t=fixture_work();a2=Client('analyst')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(c.post,f"/tasks/{t['id']}/result",{**RESULT,'value':value,'version':1}) for c,value in [(a,'1.1'),(a2,'2.2')]]
        statuses=sorted(f.result().status_code for f in futures)
    assert statuses==[200,409]
    with SessionLocal() as db:
        assert db.get(Task,t['id']).version==2
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='save_result'))==1

def test_qc_block_and_incomplete_release():
    a,h,i,q,s,t=fixture_work()
    assert a.post(f"/tasks/{t['id']}/submit",{'version':1,'reason':'Chưa có kết quả'}).status_code==422
    t=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'qc_pass':False,'version':1}))
    assert a.post(f"/tasks/{t['id']}/submit",{'version':t['version'],'reason':'QC không đạt'}).status_code==422
    s=success(q.get(f"/samples/{s['id']}"))
    assert q.post(f"/samples/{s['id']}/release",{'version':s['version'],'reason':'Thử phát hành khi chưa duyệt'}).status_code==422

def test_return_for_correction_preserves_history():
    a,h,i,q,s,t=reviewed();s=success(q.get(f"/samples/{s['id']}"))
    success(q.post(f"/samples/{s['id']}/return",{'version':s['version'],'reason':'Cần kiểm tra lại kết quả'}))
    t=success(a.get(f"/samples/{s['id']}"))['tasks'][0]
    assert t['status']=='draft' and t['reviewer_id'] is None
    success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'value':'0.14','version':t['version'],'reason':'Sửa theo hồ sơ xác nhận lại'}))
    with SessionLocal() as db:
        log=db.scalar(select(Audit).where(Audit.action=='save_result').order_by(Audit.id.desc()))
        assert log.before['value']=='0.12' and log.after['value']=='0.14'

def test_csrf_origin_and_no_session():
    anon=TestClient(app);assert anon.get('/api/samples').status_code==401
    i=Client('intake')
    assert i.http.post('/api/samples',json=SAMPLE).status_code==403
    assert i.http.post('/api/samples',json=SAMPLE,headers={'x-csrf-token':i.csrf,'origin':'https://evil.test'}).status_code==403
    assert i.http.post('/api/samples',content='x',headers={'content-type':'text/plain'}).status_code==415
    assert i.http.post('/api/samples',content='x'*70000,headers={'content-type':'application/json'}).status_code==413

def test_disable_revokes_existing_session():
    a=Client('analyst');admin=Client('admin')
    success(admin.post(f"/users/{a.me['id']}/active",{'version':1,'active':False,'reason':'Nhân viên ngừng làm việc'}))
    assert a.get('/me').status_code==401
    assert admin.post(f"/users/{admin.me['id']}/active",{'version':1,'active':False,'reason':'Tự khóa tài khoản'}).status_code==400

def test_password_rotation_revokes_all_sessions():
    a=Client('analyst');a2=Client('analyst')
    success(a.post('/password',{'old_password':PASSWORD,'new_password':'Replacement-test-2026!'}))
    assert a.get('/me').status_code==401 and a2.get('/me').status_code==401

def test_duplicate_sample_and_method():
    a=Client('analyst');i=Client('intake')
    success(a.post('/methods',METHOD),201);assert a.post('/methods',METHOD).status_code==409
    success(i.post('/samples',SAMPLE),201);assert i.post('/samples',SAMPLE).status_code==409

def test_schema_and_pagination_bounds():
    a,h,i,q,s,t=fixture_work()
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'value':'NaN','version':1}).status_code==422
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'value':'1,23','version':1}).status_code==422
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1,'status':'reviewed'}).status_code==422
    assert a.get('/samples?limit=10000').status_code==422
    assert a.get('/samples?offset=-1').status_code==422
    assert i.post('/samples',{**SAMPLE,'code':'NEW','collected_at':'2099-01-01T00:00:00Z'}).status_code==422
    assert i.post('/samples',{**SAMPLE,'code':'NEW','collected_at':'2026-01-01T00:00:00'}).status_code==422

def test_draft_method_and_wrong_assignee_not_assignable():
    a=Client('analyst');i=Client('intake');h=Client('head');other=Client('other')
    m=success(a.post('/methods',METHOD),201);s=success(i.post('/samples',SAMPLE),201)
    body={'version':1,'method_id':m['id'],'assignee_id':a.me['id'],'reason':'Thử phân công Method nháp'}
    assert i.post(f"/samples/{s['id']}/assign",body).status_code==422
    success(h.post(f"/methods/{m['id']}/approve",{'version':1,'reason':'Đã thẩm tra hồ sơ'}))
    assert i.post(f"/samples/{s['id']}/assign",{**body,'assignee_id':other.me['id']}).status_code==422

def test_security_headers_and_static_assets():
    c=TestClient(app);r=c.get('/')
    assert r.status_code==200
    assert "script-src 'self'" in r.headers['content-security-policy']
    assert r.headers['x-frame-options']=='DENY'
    assert c.get('/static/app.js').status_code==200
    assert c.get('/static/app.css').status_code==200
    a=Client('analyst')
    assert 'HttpOnly' in a.http.cookies.jar._cookies['testserver.local']['/']['vietlab_session']._rest

def test_login_throttle_database_backed():
    c=TestClient(app)
    for _ in range(20):
        assert c.post('/api/login',json={'username':'missing','password':'wrong'}).status_code==401
    assert c.post('/api/login',json={'username':'missing','password':'wrong'}).status_code==429

def test_parallel_read_scope():
    a,h,i,q,s,t=fixture_work()
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses=list(pool.map(lambda _: a.get('/samples'),range(32)))
    assert all(r.status_code==200 and r.json()['total']==1 for r in responses)

def test_v9_import_never_carries_approval_and_rejects_incomplete():
    from app.import_v9_methods import prepare
    source={'methodCode':'VOC','parameter':'Benzene','matrix':'NT','dept':'Phòng Hữu cơ','revision':'2026','unit':'µg/L','reference':'SOP-001','verification':'VER-001','status':'Đã phê duyệt'}
    rows,errors=prepare({'methodRegistry':[source]})
    assert not errors and rows[0].dept=='Hữu cơ'
    assert 'status' not in rows[0].model_dump()
    rows,errors=prepare({'methodRegistry':[{**source,'verification':''}]})
    assert errors and not rows

def test_wrong_matrix_and_double_release():
    a,h,i,q,s,t=reviewed()
    another=success(i.post('/samples',{**SAMPLE,'code':'KT.2026-001','matrix':'KT'}),201)
    assert i.post(f"/samples/{another['id']}/assign",{'version':1,'method_id':t['method_id'],'assignee_id':a.me['id'],'reason':'Thử gán sai nền mẫu'}).status_code==422
    s=success(q.get(f"/samples/{s['id']}"));body={'version':s['version'],'reason':'Phát hành nội bộ đã thẩm tra'}
    success(q.post(f"/samples/{s['id']}/release",body),201)
    assert q.post(f"/samples/{s['id']}/release",body).status_code==409

def test_head_cannot_guess_unassigned_sample_to_assign():
    a,h,i,q,s,t=fixture_work()
    hidden=success(i.post('/samples',{**SAMPLE,'code':'NT.HIDDEN'}),201)
    assert h.post(f"/samples/{hidden['id']}/assign",{'version':1,'method_id':t['method_id'],'assignee_id':a.me['id'],'reason':'Mẫu chưa thuộc phòng'}).status_code==404

def edit_body(s,**changes):
    return {k:s[k] for k in SAMPLE}|{'version':s['version'],'reason':'Chỉnh thông tin theo biên bản xác nhận'}|changes

def test_edit_sample_increments_version_and_records_before_after():
    i=Client('intake');s=success(i.post('/samples',SAMPLE),201)
    new=success(i.post(f"/samples/{s['id']}/edit",edit_body(s,location='Vị trí đã xác nhận')))
    assert new['version']==2 and new['location']=='Vị trí đã xác nhận'
    assert i.post(f"/samples/{s['id']}/edit",edit_body(s,location='Ghi đè cũ')).status_code==409
    with SessionLocal() as db:
        audit=db.scalar(select(Audit).where(Audit.action=='edit'))
        assert audit.before['location']==SAMPLE['location']
        assert audit.after['location']=='Vị trí đã xác nhận'

def test_scientific_sample_edit_invalidates_qc_and_stale_result():
    a,h,i,q,s,t=fixture_work()
    t=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}))
    s=success(i.get(f"/samples/{s['id']}"))
    success(i.post(f"/samples/{s['id']}/edit",edit_body(s,condition='Bổ sung biên bản kiểm tra tình trạng')))
    current_task=success(a.get(f"/samples/{s['id']}"))['tasks'][0]
    assert current_task['value']=='0.12' and not current_task['qc_pass']
    assert a.post(f"/tasks/{t['id']}/submit",{'version':current_task['version'],'reason':'Thử gửi khi chưa kiểm tra lại'}).status_code==422
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':t['version']}).status_code==409

def test_sample_edit_blocks_reviewed_results_and_matrix_changes():
    a,h,i,q,s,t=reviewed();s=success(i.get(f"/samples/{s['id']}"))
    assert i.post(f"/samples/{s['id']}/edit",edit_body(s,customer='Khách mới')).status_code==409
    success(q.post(f"/samples/{s['id']}/return",{'version':s['version'],'reason':'Trả lại để đối chiếu hồ sơ'}))
    s=success(i.get(f"/samples/{s['id']}"))
    assert i.post(f"/samples/{s['id']}/edit",edit_body(s,matrix='KT')).status_code==422
    assert i.post(f"/samples/{s['id']}/edit",edit_body(s,code='NT.CHANGE')).status_code==422

def test_reassign_revokes_old_access_requires_new_confirmation():
    a,h,i,q,s,t=fixture_work();peer=Client('peer')
    t=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}))
    t=success(h.post(f"/tasks/{t['id']}/reassign",{'version':t['version'],'assignee_id':peer.me['id'],'reason':'Bàn giao ca phân tích'}))
    assert not t['qc_pass'] and t['value']=='0.12' and t['author_id']==a.me['id']
    assert a.get(f"/samples/{s['id']}").status_code==404
    assert a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':t['version']}).status_code==403
    assert peer.post(f"/tasks/{t['id']}/submit",{'version':t['version'],'reason':'Chưa tự kiểm tra'}).status_code==422
    t=success(peer.post(f"/tasks/{t['id']}/result",{**RESULT,'version':t['version']}))
    assert t['author_id']==peer.me['id']
    success(peer.post(f"/tasks/{t['id']}/submit",{'version':t['version'],'reason':'Đã tự kiểm tra hồ sơ bàn giao'}))

def test_reassign_blocks_wrong_dept_inactive_and_stale():
    a,h,i,q,s,t=fixture_work();peer=Client('peer');other=Client('other');admin=Client('admin')
    body={'version':1,'assignee_id':other.me['id'],'reason':'Thử chuyển khác phòng'}
    assert h.post(f"/tasks/{t['id']}/reassign",body).status_code==422
    success(admin.post(f"/users/{peer.me['id']}/active",{'version':1,'active':False,'reason':'Khóa tài khoản thử nghiệm'}))
    assert h.post(f"/tasks/{t['id']}/reassign",{**body,'assignee_id':peer.me['id']}).status_code==422
    success(admin.post(f"/users/{peer.me['id']}/active",{'version':2,'active':True,'reason':'Mở tài khoản thử nghiệm'}))
    assert h.post(f"/tasks/{t['id']}/reassign",{**body,'assignee_id':peer.me['id'],'version':99}).status_code==409

def test_cancel_empty_sample_and_protect_terminal_state():
    i=Client('intake');s=success(i.post('/samples',SAMPLE),201)
    cancelled=success(i.post(f"/samples/{s['id']}/cancel",{'version':1,'reason':'Mẫu tạo nhầm theo biên bản'}))
    assert cancelled['status']=='cancelled'
    assert i.post(f"/samples/{s['id']}/edit",edit_body(cancelled,customer='Sửa mẫu đã hủy')).status_code==409
    assert success(i.get('/samples?status=cancelled'))['total']==1

def test_only_qa_cancels_assigned_sample_and_pending_is_removed():
    a,h,i,q,s,t=fixture_work()
    t=success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}))
    t=success(a.post(f"/tasks/{t['id']}/submit",{'version':t['version'],'reason':'Đã kiểm tra QC và kết quả'}))
    s=success(i.get(f"/samples/{s['id']}"));body={'version':s['version'],'reason':'Khách hàng yêu cầu hủy mẫu'}
    assert i.post(f"/samples/{s['id']}/cancel",body).status_code==403
    success(q.post(f"/samples/{s['id']}/cancel",body))
    assert success(h.get('/dashboard'))['pending_review']==0
    assert h.post(f"/tasks/{t['id']}/review",{'version':t['version'],'decision':'approve','reason':'Thử duyệt mẫu đã hủy'}).status_code==409
    with SessionLocal() as db: assert db.get(Task,t['id']).value=='0.12'

def test_retired_method_blocks_new_assignments_keeps_existing_work():
    a,h,i,q,s,t=fixture_work()
    m=success(h.get('/methods'))['items'][0]
    m=success(h.post(f"/methods/{m['id']}/retire",{'version':m['version'],'reason':'Ngừng phân công phiên bản cũ'}))
    assert m['status']=='retired'
    new=success(i.post('/samples',{**SAMPLE,'code':'NT.NEW'}),201)
    assert i.post(f"/samples/{new['id']}/assign",{'version':1,'method_id':m['id'],'assignee_id':a.me['id'],'reason':'Thử phân công Method đã ngừng'}).status_code==422
    success(a.post(f"/tasks/{t['id']}/result",{**RESULT,'version':1}))
