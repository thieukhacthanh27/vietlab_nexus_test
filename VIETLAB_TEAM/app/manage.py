"""Explicit initialization; no default users, passwords or auto schema writes at startup."""
import argparse
import getpass
from sqlalchemy import select
from .db import Base, engine, SessionLocal, User
from .main import ph, audit
from .schemas import NewUser

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['init-db','create-admin','reset-password']);args=parser.parse_args()
    if args.command=='init-db':
        Base.metadata.create_all(engine);print('Schema 10.0-pilot initialized.');return
    name=input('Username: ').strip()
    password=getpass.getpass('New password (12+ chars): ')
    if password!=getpass.getpass('Repeat password: '): raise SystemExit('Passwords do not match.')
    if len(password)<12 or len(password)>128: raise SystemExit('Password length must be 12–128.')
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.username==name))
        if args.command=='create-admin':
            if user: raise SystemExit('Account already exists.')
            data=NewUser(username=name,password=password,full_name=input('Full name: ').strip(),role='admin',dept='Điều hành')
            user=User(**data.model_dump(exclude={'password'}),password_hash=ph.hash(password));db.add(user);db.flush()
            audit(db,None,'bootstrap_admin','user',user.id,'Created through server console')
        else:
            if not user: raise SystemExit('Account not found.')
            from .db import AuthSession
            from sqlalchemy import delete
            user.password_hash=ph.hash(password)
            db.execute(delete(AuthSession).where(AuthSession.user_id==user.id))
            audit(db,None,'console_reset_password','user',user.id,'Reset through authorized server console; sessions revoked')
        db.commit();print('Completed.')

if __name__=='__main__':main()
