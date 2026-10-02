import os
import psycopg2
import redis
from flask import Flask, jsonify, request

app = Flask(__name__)
cache = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), decode_responses=True)

def db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

def init_db():
    with db() as conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, title TEXT NOT NULL)")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/tasks")
def list_tasks():
    cache.incr("hits")
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title FROM tasks ORDER BY id")
        rows = [{"id": r[0], "title": r[1]} for r in cur.fetchall()]
    return jsonify(tasks=rows, hits=int(cache.get("hits")), served_by=os.uname().nodename)

@app.post("/api/tasks")
def add_task():
    title = (request.get_json(silent=True) or {}).get("title")
    if not title:
        return {"error": "title required"}, 400
    with db() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO tasks (title) VALUES (%s) RETURNING id", (title,))
        new_id = cur.fetchone()[0]
    return {"id": new_id, "title": title}, 201

init_db()
