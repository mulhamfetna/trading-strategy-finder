import os, re, time, psycopg2
u = os.environ["WSH_STORAGE_URL"]
usr, pw, host, port, db = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(\w+)", u).groups()
c = psycopg2.connect(host=host, port=port or 5432, user=usr, password=pw, dbname=db, connect_timeout=8)
c.autocommit = True
cur = c.cursor(); cur.execute("SET statement_timeout=20000")
cur.execute("select study_id from studies where study_name='wshent1_4h'"); sid = cur.fetchone()[0]

def ncomplete():
    cur.execute("select count(*) from trials where study_id=%s and state='COMPLETE'", (sid,))
    return cur.fetchone()[0]

def nrun():
    cur.execute("select count(*) from trials where study_id=%s and state='RUNNING'", (sid,))
    return cur.fetchone()[0]

a = ncomplete(); r = nrun(); t0 = time.time()
time.sleep(60)
b = ncomplete(); dt = time.time() - t0
rate = (b - a) / dt * 60.0
rem = max(0, 50000 - b)
eta = (rem / rate) if rate > 0 else float("inf")
print(f"complete_start={a} complete_now={b} running={r} dt={dt:.0f}s "
      f"rate={rate:.0f}/min remaining={rem} eta_min={eta:.1f}")
