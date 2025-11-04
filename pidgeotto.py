import schedule
import smtplib
from email.message import EmailMessage
import rotom
import datetime
import discord

EMAIL, PASSWORD = rotom.enviromentals('EMAIL', 'EMAIL_PASSWORD')

def get_report():
    reports = rotom.postgresql(
        "SELECT columns FROM tables WHERE status = 'ready'",
        rotom.enviromentals('POSTGRESQL_TABLE_FOR_REPORTS'),
        ('id', 'body', 'username', 'creation')
    )
    
    if reports:
        for report in reports:
            satisfactory = []
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
                    satisfactory.append(query)
            send_email(info.get('email', ''), 'PyPikachu', html_template(satisfactory))
            try:
                rotom.postgresql(
                    f"UPDATE tables SET columns WHERE id = '{report.get('id', '')}'",
                    rotom.enviromentals('POSTGRESQL_TABLE_FOR_REPORTS'),
                    tuple([key+' = %s' for key in ("status", "delivery")]),
                    {'status': 'delivered', 'delivery': datetime.datetime.now(datetime.timezone.utc)}
                )
            except Exception as e:
                with open('logs/messenger.log', 'a') as fp: fp.write(f'{e}\n')

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
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f'PyPikachu <{EMAIL}>'
    msg['To'] = to_email

    msg.set_content("This email requires an HTML viewer.")
    msg.add_alternative(body, subtype='html')

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)

schedule.every(3).minutes.do(get_report)

if __name__ == "__main__":
    get_report()
    while True:
        schedule.run_pending()