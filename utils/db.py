"""
Database utility module.
Provides a small wrapper around mysql-connector-python with a connection
pool, plus helper functions for running queries and fetching results as
dictionaries.
"""
import mysql.connector
from mysql.connector import pooling
from flask import current_app, g

_pool = None


def init_pool(app):
    global _pool
    pool_kwargs = dict(
        pool_name="fitsync_pool",
        pool_size=int(app.config.get("MYSQL_POOL_SIZE", 5)),
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"],
        autocommit=False,
    )

    # Managed MySQL providers (Aiven, PlanetScale, etc.) require TLS.
    # Set MYSQL_SSL_CA to the path of the downloaded CA certificate to
    # enable a verified TLS connection. If not set, connects without SSL
    # (fine for local MySQL on localhost).
    ssl_ca = app.config.get("MYSQL_SSL_CA")
    if ssl_ca:
        pool_kwargs["ssl_ca"] = ssl_ca
        pool_kwargs["ssl_verify_cert"] = True

    _pool = pooling.MySQLConnectionPool(**pool_kwargs)


def get_conn():
    if "db_conn" not in g:
        g.db_conn = _pool.get_connection()
    return g.db_conn


def close_conn(e=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def query_all(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    return rows


def query_one(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    row = cur.fetchone()
    cur.close()
    return row


def execute(sql, params=None, return_id=False):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    last_id = cur.lastrowid
    rowcount = cur.rowcount
    cur.close()
    return last_id if return_id else rowcount


def executemany(sql, param_list):
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(sql, param_list)
    conn.commit()
    cur.close()
