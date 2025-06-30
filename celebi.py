import schedule
import arceus
import rotom
import json
import datetime

models = {}

def run_script(tasks: list[dict], AI=None):
    for task in tasks:
        results = arceus.main(
            task.get('defect', ''),
            task.get('threshold', 0),
            USE_LOCAL_STORAGE=False,
            USE_RGB=True,
            download_dataset=True,
            AI=AI
        )
        #with open('logs/setup.log', 'a') as fp: fp.write(f'1 {results[0]}\n')
        for result in results:
            if 'image' in result:
                result.pop('image')
        report(results, task.get('id', ''), task.get('username', ''))

def report(results: list, id: str, username: str):
    with open('logs/setu.log', 'a') as fp: fp.write(f'{results}\n')
    try:
        rotom.postgresql(
            "INSERT INTO tables (columns) VALUES (values)",
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_REPORTS'),
            ('taskid', 'username', 'body', 'creation', 'status'),
            {'taskid': id, 'username': username, 'body': json.dumps(results), 'creation': datetime.datetime.now(datetime.timezone.utc), 'status': 'ready'}
    )
    except Exception as e:
        with open('logs/setup.log', 'a') as fp: fp.write(f'2 {e}\n')
    else:
        try:
            rotom.postgresql(
                f"UPDATE tables SET epoch = epoch - 1, status = CASE WHEN epoch <= 1 THEN 'completed' ELSE status END WHERE id = {id};",
                rotom.enviromentals('POSTGRESQL_TABLE_FOR_TASKS')
            )
        except Exception as e:
            with open('logs/setup.log', 'a') as fp: fp.write(f'3 {e}\n')
            pass
                
def get_tasks():
    template = ('defect', 'threshold', 'hash', 'id', 'username')
    rows = rotom.postgresql(
        "SELECT columns FROM tables WHERE status != 'completed' OR epoch != 0",
        rotom.enviromentals('POSTGRESQL_TABLE_FOR_TASKS'),
        template
    )
    
    tasks: list[dict[str, str | int]] = []
    for values in rows:
        task = {}
        for key in template:
            if key in values:
                task[key] = values.get(key, None)
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

def main():
    tasks = get_tasks()
    run_script(tasks)
# ----------------------------
# ⏰ Scheduler
# ----------------------------
#schedule.every(1).days.do(establish_model)
schedule.every(3).minutes.do(main)

if __name__ == "__main__":
    #establish_model()  # Ensure model is available before first run
    main()
    while True:
        schedule.run_pending()