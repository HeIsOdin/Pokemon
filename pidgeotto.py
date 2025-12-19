import schedule
import requests
import rotom
import datetime
import discord

EMAIL, MAILGUN_BASE_URL, MAILGUN_API_KEY = rotom.enviromentals('EMAIL', 'MAILGUN_BASE_URL' ,'MAILGUN_API_KEY')

def get_report():
    reports = rotom.postgresql(
        "SELECT columns FROM tables WHERE status = 'ready'",
        rotom.enviromentals('POSTGRESQL_TABLE_FOR_REPORTS'),
        ('id', 'body', 'username', 'creation')
    )
    return reports
    
def process_reports(reports: list):
    satisfactory = []
    for report in reports:
        queries = report.get('body', [])
        info = rotom.postgresql(
            f"SELECT columns FROM tables WHERE username = '{report.get('username', '')}'",
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_USERS'),
            ('email', 'discord'),
            limit=1
        ).pop()

        for query in queries:
            if query.get('truth', '') == True:
                query.update({'image_url': f"<img src='{query.get('image_url', '')}' alt='pokemon card'/>"})
                query.update({'product_url': f"<a href='{query.get('product_url', '')}'>Click Me!</a>"})
        satisfactory.append({
            'id': report.get('id', ''),
            'email': info.get('email', ''),
            'queries': queries,})
    return satisfactory

def deliver_reports(deliverable: dict):
    send_email(
            deliverable.get('email', ''),
            'PyPikachu',
            html_template(deliverable.get('queries', []))
    )

def update_status(id: str = ''):
    try:
        rotom.postgresql(
            f"UPDATE tables SET columns WHERE id = '{id}'",
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_REPORTS'),
            tuple([key+' = %s' for key in ("status", "delivery")]),
            {'status': 'delivered','delivery': datetime.datetime.now(datetime.timezone.utc)}
        )
    except Exception as e:
        with open('logs/messenger.log', 'a') as fp:
            fp.write(f'{e}\n')

def html_template(reports: list):
    def render_table_from_data(data: list[dict[str, str | int]]) -> str:
        if not data:
            return "<p>No results found.</p>"

        headers = data[0].keys()
        rows = [
            "<tr>" + "".join(f"<th>{key.capitalize()}</th>" for key in headers) + "</tr>"
        ]
        for row in data:
            rows.append(
                "<tr>" + "".join(f"<td>{row.get(key, '')}</td>" for key in headers) + "</tr>"
            )
        return f"<table>{''.join(rows)}</table>"

    with open('template.html', 'r') as fp: template = fp.read()
    return ''.join((template, f"""
        <body class="is-preload">
            <div id="task-history-container">
                {render_table_from_data(reports)}
            </div>
        </body></html>
        """
    ))

def send_email(to_email: str, subject: str, body: str):
    if not to_email or not subject or not body:
        return
    return requests.post(
        MAILGUN_BASE_URL,
  		auth=("api", MAILGUN_API_KEY),
  		data={"from": EMAIL,
			"to": to_email,
  			"subject": subject,
            "text": "Your email client does not support HTML emails.",
            "html": body})

def main():
    reports = get_report()
    if not reports:
        return
    deliverables = process_reports(reports)
    for deliverable in deliverables:
        deliver_reports(deliverable)
        update_status(deliverable.get('id', ''))

schedule.every(3).minutes.do(main)

if __name__ == "__main__":
    while True:
        schedule.run_pending()