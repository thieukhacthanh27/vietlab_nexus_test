"""Import only validated Method metadata from a V9 JSON backup; default is dry-run.
No results, samples, accounts, approvals or demo users are imported.
"""
import argparse
import json
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy import select
from .db import SessionLocal, Method, User
from .schemas import NewMethod
from .main import audit

MAP={'Phòng Hóa lý':'Hóa lý','Phòng Hữu cơ':'Hữu cơ','Phòng Kim loại':'Kim loại','Phòng Vi sinh':'Vi sinh','Phòng Quan trắc':'Quan trắc'}
FIELDS={'code':'methodCode','parameter':'parameter','matrix':'matrix','dept':'dept','revision':'revision','unit':'unit','sop':'reference','verification':'verification'}

def prepare(data):
    rows=data.get('methodRegistry') if isinstance(data,dict) else None
    if not isinstance(rows,list): raise ValueError('JSON phải có methodRegistry dạng danh sách.')
    if len(rows)>2000: raise ValueError('Tối đa 2000 Method mỗi lần chuyển.')
    valid=[];errors=[];seen=set()
    for index,row in enumerate(rows,1):
        try:
            if not isinstance(row,dict): raise ValueError('Bản ghi phải là object.')
            item={target:str(row.get(source) or '').strip() for target,source in FIELDS.items()}
            item['dept']=MAP.get(item['dept'],item['dept'])
            model=NewMethod(**item)
            key=tuple(getattr(model,k) for k in ('code','parameter','matrix','dept','revision'))
            if key in seen: raise ValueError('Trùng liên kết và phiên bản trong file.')
            seen.add(key);valid.append(model)
        except ValidationError as exc:
            errors.append({'row':index,'fields':[str(e['loc'][0]) for e in exc.errors()]})
        except ValueError as exc: errors.append({'row':index,'error':str(exc)})
    return valid,errors

def main():
    p=argparse.ArgumentParser();p.add_argument('backup');p.add_argument('--apply',action='store_true');p.add_argument('--actor');args=p.parse_args()
    path=Path(args.backup)
    if path.stat().st_size>20*1024*1024: raise SystemExit('Tối đa 20 MiB.')
    models,errors=prepare(json.loads(path.read_text(encoding='utf-8-sig')))
    print(json.dumps({'valid':len(models),'errors':errors,'mode':'apply' if args.apply else 'dry-run'},ensure_ascii=False,indent=2))
    if errors: raise SystemExit('Chưa ghi dữ liệu. Sửa các dòng thiếu/sai rồi chạy lại.')
    if not args.apply:return
    if not args.actor:raise SystemExit('--actor phải là username quản trị thực hiện chuyển đổi.')
    with SessionLocal() as db:
        actor=db.scalar(select(User).where(User.username==args.actor,User.active==True,User.role=='admin'))
        if not actor:raise SystemExit('Không tìm thấy quản trị viên hoạt động.')
        for m in models:
            existing=db.scalar(select(Method.id).where(*(getattr(Method,k)==getattr(m,k) for k in ('code','parameter','matrix','dept','revision'))))
            if existing:raise SystemExit('Có Method trùng cơ sở dữ liệu; giao dịch được hoàn tác.')
            obj=Method(**m.model_dump(),author_id=actor.id,status='draft')
            db.add(obj);db.flush()
            audit(db,actor,'import_v9','method',obj.id,'Chuyển danh mục V9; bắt buộc duyệt lại',after=m.model_dump())
        db.commit()
    print(f'Đã nhập {len(models)} Method ở trạng thái nháp. Không mang trạng thái phê duyệt từ bản cũ.')

if __name__=='__main__':main()
