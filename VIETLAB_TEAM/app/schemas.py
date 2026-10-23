from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal['admin','intake','analyst','head','qa','director']
Dept = Literal['Hóa lý','Hữu cơ','Kim loại','Vi sinh','Quan trắc','Điều hành']
Matrix = Literal['NT','NM','NS','KT','KLV','KXQ','DAT','TRAMTICH']

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Login(Input):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-z0-9._-]+$')
    password: str = Field(min_length=1, max_length=128)

class NewUser(Login):
    full_name: str = Field(min_length=2, max_length=160)
    role: Role
    dept: Dept
    @field_validator('password')
    @classmethod
    def password_length(cls, v):
        if len(v) < 12: raise ValueError('Mật khẩu tối thiểu 12 ký tự.')
        return v

class Version(Input):
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)

class SetActive(Version):
    active: bool

class ChangePassword(Input):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

class NewMethod(Input):
    code: str = Field(min_length=1, max_length=80)
    parameter: str = Field(min_length=1, max_length=160)
    matrix: Matrix
    dept: Dept
    revision: str = Field(min_length=1, max_length=60)
    unit: str = Field(min_length=1, max_length=40)
    sop: str = Field(min_length=1, max_length=160)
    verification: str = Field(min_length=1, max_length=160)

class NewSample(Input):
    code: str = Field(min_length=3, max_length=80, pattern=r'^[A-Za-z0-9._/-]+$')
    customer: str = Field(min_length=2, max_length=200)
    contract: str = Field(min_length=1, max_length=100)
    matrix: Matrix
    location: str = Field(min_length=1, max_length=300)
    collected_at: datetime
    due: date
    condition: str = Field(min_length=5, max_length=500)
    @field_validator('collected_at')
    @classmethod
    def valid_collection(cls, v):
        if v.tzinfo is None: raise ValueError('Thời gian lấy mẫu cần múi giờ.')
        if v > datetime.now(timezone.utc): raise ValueError('Thời gian lấy mẫu không được ở tương lai.')
        return v

class Assign(Version):
    method_id: int = Field(ge=1)
    assignee_id: int = Field(ge=1)

class Result(Version):
    value: str = Field(min_length=1, max_length=100)
    qc_pass: bool
    qc_note: str = Field(min_length=5, max_length=1000)
    evidence_ref: str = Field(min_length=3, max_length=300)
    @field_validator('value')
    @classmethod
    def valid_value(cls, v):
        import re
        from decimal import Decimal
        if v in ['<LOQ','<MDL','ND']: return v
        if not re.fullmatch(r'[<>≤≥]?\s*-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', v):
            raise ValueError('Nhập số dùng dấu chấm, <LOQ, <MDL hoặc ND.')
        n = re.sub(r'^[<>≤≥]\s*','',v)
        if not Decimal(n).is_finite() or abs(Decimal(n)) > Decimal('1e100'):
            raise ValueError('Giá trị vượt phạm vi.')
        return v

class Review(Version):
    decision: Literal['approve','return']

class EditSample(NewSample, Version):
    pass

class Reassign(Version):
    assignee_id: int = Field(ge=1)
