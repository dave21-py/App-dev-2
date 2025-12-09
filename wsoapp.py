# Requires the Bottle and MySQL libraries
# To use this app:
#   pip install mysql-connector-python
#   pip install flask

import time
import html
from datetime import datetime

from flask import Flask, request
from mysql.connector import connect
import dbconfig

app = Flask(__name__)

HTML_MAIN = """<html>
<head>
    <title>Service Order Generator</title>
</head>
<body>
    <h1>Service Order Generator</h1>
    <h2>Select a Service!</h2>
    <table border='1' cellpadding='5' cellspacing='0'>
        <tr>
            <th>Date/Time</th>
            <th>Theme</th>
            <th>Link</th>
        </tr>
        {0}
    </table>
</body>
</html>"""

HTML_DETAILS = """<html>
<head>
    <title>Service Details</title>
</head>
<body>
    {0}
    <a href="/">BACK TO SERVICE LIST</a>

    <h3>Service Events</h3>
    <table border='1' cellpadding='5' cellspacing='0'>
        <tr>
            <th>Sequence Number</th>
            <th>Event</th>
            <th>Song Title</th>
            <th>Person</th>
            <th>Notes</th>
        </tr>
        {1}
    </table>

    <h3>Create a New Service</h3>
    <p>(Fields with * are required)</p>
    <form method='post' action='/create_service'>
        <label>*Date and Time:<br>
            Format: YYYY-MM-DD HH:MM:SS<br>
            <input type='text' name='new_datetime' value='{2}' required>
        </label><br><br>

        <label>Theme:<br>
            <input type='text' name='theme' value='{3}'>
        </label><br><br>

        <label>Songleader:<br>
            <input type='text' name='songleader' value=''>
        </label><br><br>

        <input type='hidden' name='template_id' value='{4}'>
        <input type='submit' value='Create Service'>
    </form>
</body>
</html>"""


@app.route("/")
def index():
    # We don't close the following explicitly because they are automatically closed
    # when the variables go out of scope when index() returns
    con = connect(
        user=dbconfig.DB_USER,
        password=dbconfig.DB_PASS,
        database=dbconfig.DB_NAME,
        host=dbconfig.DB_HOST,
    )
    cursor = con.cursor()

    # select all the services ordered by date
    cursor.execute("""
        SELECT Service_ID, Svc_DateTime, Theme_Event
        FROM service 
        ORDER BY Svc_DateTime 
        DESC""")
    result = cursor.fetchall()

    table_rows = ""
    for row in result:
        (service_id, svc_datetime, theme) = row

        # handle the null values
        if theme is None:
            theme = ""
        

        link = f"<a href='/service_details/{service_id}'>Select</a>"


        table_row = f"""
        <tr>
            <td>{svc_datetime}
            <td>{theme}
            <td>{link}
        </tr>
        """
        table_rows += table_row


    cursor.close()
    con.close()

    return HTML_MAIN.format(table_rows)

@app.route('/service_details/<id>')
def details(id):
    time = request.args.get('time', "")
    theme = request.args.get('theme', "")
    songleader = request.args.get('songleader', "")

    con = connect(
        user=dbconfig.DB_USER, 
        password=dbconfig.DB_PASS, 
        database=dbconfig.DB_NAME, 
        host=dbconfig.DB_HOST
    )
    con.autocommit = True
    cursor = con.cursor()

    cursor.execute("""
        SELECT 
            Svc_DateTime, Theme_Event, Seq_Num, Description,
            Title, CONCAT(person.First_Name, ' ', person.Last_Name) AS Person, Notes
        FROM service
        JOIN service_item ON service.Service_ID = service_item.Service_ID
        JOIN event_type ON service_item.Event_Type_ID = event_type.Event_Type_ID
        LEFT JOIN person ON service_item.Person_ID = person.Person_ID
        WHERE service.Service_ID = %s
    """, (id,))

    result = cursor.fetchall()

    # Build table
    tableRows = ""
    for row in result:
        Svc_DateTime, Theme_Event, Seq_Num, Description, Title, Person, Notes = row
        tableRows += f"""
        <tr>
            <td>{Seq_Num}</td>
            <td>{Description}</td>
            <td>{Title}</td>
            <td>{Person}</td>
            <td>{Notes}</td>
        </tr>
        """

    # Build header using first row only
    if result:
        Svc_DateTime, Theme_Event, Seq_Num, Description, Title, Person, Notes = result[0]
        header = f"""
        <h1>{Theme_Event}</h1>
        <h3>Songleader: {Person}</h3>
        <p>Service held at: {Svc_DateTime}</p>
        """
        theme = Theme_Event
    else:
        header = "<h1>No service found.</h1>"

    cursor.close()
    con.close()

    return HTML_DETAILS.format(header, tableRows, time, theme, id)


# Launch the local web server
if __name__ == "__main__":
    app.run(host="localhost", debug=True)
