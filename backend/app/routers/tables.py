"""结果表 CRUD 接口：列表/详情/新建（一步含列）/更新/删除/复制"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import database as db

router = APIRouter(prefix="/api/tables", tags=["tables"])


class ColumnIn(BaseModel):
    field: str
    title: str
    type: str = "text"
    required: bool = False
    options: list[str] = []
    description: str = ""


class TableCreate(BaseModel):
    name: str
    description: str = ""
    columns: list[ColumnIn] = []


class TableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ColumnsUpdate(BaseModel):
    columns: list[ColumnIn]


@router.get("")
def list_tables():
    return db.list_tables()


@router.get("/{table_id}")
def get_table(table_id: int):
    table = db.get_table(table_id)
    if not table:
        raise HTTPException(404, "结果表不存在")
    table["columns"] = db.get_columns(table_id)
    return table


@router.post("")
def create_table(body: TableCreate):
    if not body.name.strip():
        raise HTTPException(400, "表名不能为空")
    if not body.columns:
        raise HTTPException(400, "至少需要配置一列")
    try:
        return db.create_table(body.name.strip(), body.description.strip(), [c.model_dump() for c in body.columns])
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/{table_id}")
def update_table(table_id: int, body: TableUpdate):
    try:
        db.update_table(table_id, body.name, body.description)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{table_id}")
def delete_table(table_id: int):
    db.delete_table(table_id)
    return {"ok": True}


@router.post("/{table_id}/copy")
def copy_table(table_id: int, body: TableUpdate):
    if not body.name or not body.name.strip():
        raise HTTPException(400, "新表名不能为空")
    try:
        return db.copy_table(table_id, body.name.strip())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{table_id}/columns")
def get_columns(table_id: int):
    return db.get_columns(table_id)


@router.put("/{table_id}/columns")
def save_columns(table_id: int, body: ColumnsUpdate):
    try:
        db.save_columns(table_id, [c.model_dump() for c in body.columns])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
