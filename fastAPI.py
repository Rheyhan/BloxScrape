from typing import *
from fastapi import FastAPI, Query, HTTPException
import os
import sqlite3

DB_PATH = "robloxaccessory.db"
TABLE_NAME = "roblox_accessories"

app = FastAPI(title="BloxScrape API", version="1.0.0")

# For API usage
@app.get("/")
def root():
    return {"message": "Welcome to the BloxScrape API. Visit /docs for API documentation."}

def get_connection() -> sqlite3.Connection:
    '''
    Get a  database connection with row factory set to sqlite3.Row. Basically change the return type to dict-like.

    Returns
    -------
    - sqlite3.Connection
        Database connection
    '''
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db():
    '''
    Ensure the database exists before performing any operations
    '''
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail=f"Database not found at {DB_PATH}")
    
def build_filters(  category: Optional[str], creator: Optional[str],
                    IsVerified: Optional[bool], IsLimited: Optional[bool]):
    clauses = []
    params = []

    if creator:
        clauses.append("Creator = ?")
        params.append(creator)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if IsVerified is not None:
        clauses.append("IsVerified = ?")
        params.append(1 if IsVerified else 0)
    if IsLimited is not None:
        clauses.append("IsLimited = ?")
        params.append(1 if IsLimited else 0)
        
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where_sql, params

@app.get("/health")
def health():
    '''
    Health check endpoint
    '''
    return {"status": "ok"}


@app.get("/items")
def list_items(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), creator: Optional[str] = None,
               category: Optional[str] = None, verified: Optional[bool] = None, limited: Optional[bool] = None):
    '''
    List items with optional filters and pagination

    Parameters
    ----------
    - limit : int
        Number of items to return (default 50, max 500)
    - offset : int
        Number of items to skip (default 0)
    - creator : Optional[str]
        Filter by creator name
    - category : Optional[str]
        Filter by category
    - verified : Optional[bool]
        Filter by verified status
    - limited : Optional[bool]
        Filter by limited status
    '''

    ensure_db()

    where_sql, params = build_filters(creator, category, verified, limited)
    sql = f"SELECT * FROM {TABLE_NAME}{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"
    params = params + [limit, offset]

    rows = []
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute(sql, params).fetchall()
    finally:
        if conn:
            conn.close()

    return {"count": len(rows), "items": [dict(r) for r in rows]}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    ensure_db()
    conn = None
    row = None
    try:
        conn = get_connection()
        row = conn.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (item_id,)
        ).fetchone()
    finally:
        if conn:
            conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return dict(row)

@app.get("/stats")
def stats():
    '''
    Get database statistics
    '''
    ensure_db()
    conn = None
    try:
        conn = get_connection()
        total = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        latest = conn.execute(
            f"SELECT MAX(timeCollected) FROM {TABLE_NAME}"
        ).fetchone()[0]
        verified = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE IsVerified = 1"
        ).fetchone()[0]
        limited = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE IsLimited = 1"
        ).fetchone()[0]
        category = conn.execute(f"SELECT category, COUNT(*) FROM {TABLE_NAME} GROUP BY category").fetchall()
    finally:
        if conn:
            conn.close()
    return {
        "total": total,
        "verified": verified,
        "limited": limited,
        "latest_timeCollected": latest,
        "detail": {i['category']: i[1] for i in category[1:]}
    }

@app.get("/recent")
def recent(limit: int = Query(10, ge=1, le=100)):
    '''
    Get the most recent items added to the database
    '''
    ensure_db()
    conn = None
    rows = []
    try:
        conn = get_connection()
        rows = conn.execute(
            f"SELECT * FROM {TABLE_NAME} ORDER BY timeCollected DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        if conn:
            conn.close()
    return {"items": [dict(r) for r in rows]}