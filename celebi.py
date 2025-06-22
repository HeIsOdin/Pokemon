import schedule
import arceus
import rotom
import psycopg2
import json
import datetime

models = {}

def run_script(tasks: list[dict], AI=None):
    for task in tasks:
        results = arceus.main(
            task.get('defect', ''),
            task.get('threshold', ''),
            USE_LOCAL_STORAGE=False,
            USE_RGB=True,
            download_dataset=True,
            AI=AI
        )
        report(results, task.get('id', ''), task.get('username', ''))

def report(results: list, id: str, username: str):
    DATABASE, USER, PASSWORD, HOST, PORT, TABLE, TASKS = rotom.enviromentals(
        'POSTGRESQL_DBNAME',
        'POSTGRESQL_USER',
        'POSTGRESQL_PASSWD',
        'POSTGRESQL_HOST',
        'POSTGRESQL_PORT',
        'POSTGRESQL_TABLE_FOR_REPORTS',
        'POSTGRESQL_TABLE_FOR_TASKS'
    )
    template = ('id', 'username', 'body', 'creation', 'status')
    sql = f"""
        INSERT INTO {TABLE} ({', '.join(template)})
        VALUES ({', '.join(['%s' for _ in template])})
    """
    data = (id, username, json.dumps(results), datetime.datetime.now(datetime.timezone.utc), 'ready')
    try:
        conn = psycopg2.connect(database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT)
        cursor = conn.cursor()
        cursor.execute(sql, data)
        conn.commit()
    
    except Exception as e:
        print(e)
    else:
        try:
            sql = f"""
                UPDATE {TASKS}
                SET epoch = epoch - 1,
                status = 
                    CASE WHEN epoch <= 1 THEN 'completed'
                    ELSE status
                END
                WHERE id = %s;
            """
            cursor.execute(sql, (id,))
            conn.commit()
        except:
            pass
    finally:
        cursor.close()
        conn.close()
                
def get_tasks():
    DATABASE, USER, PASSWORD, HOST, PORT, TABLE = rotom.enviromentals(
        'POSTGRESQL_DBNAME',
        'POSTGRESQL_USER',
        'POSTGRESQL_PASSWD',
        'POSTGRESQL_HOST',
        'POSTGRESQL_PORT',
        'POSTGRESQL_TABLE_FOR_TASKS'
    )
    conn = psycopg2.connect(database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT)
    cursor = conn.cursor()
    template = ('defect', 'threshold', 'hash', 'id', 'username')
    sql = f"SELECT {', '.join(template)} FROM {TABLE} WHERE status != 'completed' OR epoch != 0"
    cursor.execute(sql)
    
    rows = cursor.fetchall()
    tasks: list[dict[str, str | int]] = []
    for values in rows:
        task = {}
        for key, value in zip(template, values):
            task[key] = value
        tasks.append(task)

    tasks = drop_redundancy(tasks)
    return tasks

def drop_redundancy(tasks: list[dict[str, str | int]]):
    for task in tasks:
        pass
    return tasks

def establish_model():
    global AI
    #AI = porygon.main()

def _main():
    tasks = get_tasks()
    run_script(tasks)
# ----------------------------
# ⏰ Scheduler
# ----------------------------
#schedule.every(1).days.do(establish_model)
schedule.every(3).minutes.do(_main)

if __name__ == "__main__":
    #establish_model()  # Ensure model is available before first run
    _main()
    while True:
        schedule.run_pending()