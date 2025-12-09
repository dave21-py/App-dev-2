# Requires the Bottle and MySQL libraries
# To use this app:
#   pip install mysql-connector-python
#   pip install flask


import time
from datetime import datetime

from flask import Flask, request
from mysql.connector import connect
import dbconfig

app = Flask(__name__)


HTML_MAIN = """<html><head><title>Service Order Generator</title></head><body>
    <h1>Service Order Generator</h1>
    <h2>Select a Service!</h2>
        <table border='1'>
        <tr>
            <th>Date/Time</th>
            <th>Theme</th>
            <th>Link</th>
        </tr>
        {0}
        </table>
        </body></html>"""

HTML_DETAILS = """<html><head><title>Service Details</title></head><body>
    <h1>Service Details</h1>
    <h3>Service Info</h3>
    <p><b>Date/Time:</b> {0}</p>
    <p><b>Theme:</b> {1}</p>
    <p><b>Songleader:</b> {2}</p>

    <h3>Events</h3>
    <table border='1'>
        <tr>
            <th>Seq</th>
            <th>Type</th>
            <th>Title</th>
            <th>Person</th>
            <th>Notes</th>
        </tr>
        {3}
        </table>


        <hr>
        <h3>Create new Service</h3>
        <form action="/create_service" method="POST">
        <input type="hidden" name="template_id" value="{6}"> 
        <p><label>Date/Time (YYYY-MM-DD HH:MM:SS) *:</label><br>
        <input type="text" name="new_date" value="{4}"></p>
        <p><label>Theme:</label><br>
        <input type="text" name="new_theme" value="{1}"></p>
        <p><label>Songleader:</label><br>
        <select name="new_songleader">
        <option value="">(NO Songleader)</option>
        {5}</select></p>
        <input type="submit" value="Create Service">
        </form>
        <br>
        <a href="/">Back to Home Page</a>
        </body></html>"""
        

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
    sql = "select Service_ID, Svc_DateTime, Theme_Event from service order by Svc_DateTime DESC"
    cursor.execute(sql)
    result = cursor.fetchall()




    table_rows = ""
    for row in result:
        (service_id, svc_datetime, theme) = row

        # handle the null values
        if theme is None:
            theme = ""
        

        link = f"<a href='/service_details?id={service_id}'>Select</a>"


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


@app.route("/service_details")
def service_details():
    service_id = request.args.get("id")

    con = connect(
        user=dbconfig.DB_USER,
        password=dbconfig.DB_PASS,
        database=dbconfig.DB_NAME,
        host=dbconfig.DB_HOST,
    )
    cursor = con.cursor()

    # Service Info + Songleader Name
    sql_info = """
    select s.Svc_DateTime, s.Theme_Event, CONCAT(p.First_Name, ' ', p.Last_Name) as songleader_name
    from service s
    left join fills_role fr on s.Service_ID = fr.Service_ID AND fr.Role_Type = 'S'
    left join person p on fr.Person_ID = p.Person_ID
    where s.Service_ID = %s
    """

    cursor.execute(sql_info, (service_id,))
    result = cursor.fetchall()

    # initialise the variables
    svc_datetime = ""
    theme = ""
    songleader = ""

    for row in result:
        (svc_datetime, theme, songleader) = row

    if theme is None: theme = ""
    if songleader is None: songleader = "None"  

    # Events
    sql_events = """
    select si.Seq_Num, et.Description, s.Title, si.Title, p.First_Name, p.Last_Name, si.Notes
    from service_item si
    join event_type et on si.Event_Type_ID = et.Event_Type_ID
    left join song s on si.Song_ID = s.Song_ID
    left join person p on si.Person_ID = p.Person_ID
    where si.Service_ID = %s
    order by si.Seq_Num
    """  

    cursor.execute(sql_events, (service_id,))
    events_result = cursor.fetchall()

    event_rows = ""
    for row in events_result:
        (seq, etype, song_title, item_title, fname, lname, notes) = row

        display_title = ""
        if song_title:
            display_title = song_title
        elif item_title:
            display_title = item_title

        # FORMAT NAME
        person_name = ""
        if fname:
            person_name = f"{fname} {lname}"

        if notes is None:
            notes = ""

        event_rows += f"""
        <tr>
        <td>{seq}</td>
        <td>{etype}</td>
        <td>{display_title}</td>
        <td>{person_name}</td>
        <td>{notes}</td>
        </tr>
        """

    sql_leaders = """
    select distinct First_Name, Last_Name
    from person p
    join fills_role fr on p.Person_ID = fr.Person_ID
    where fr.Role_Type = 'S'
    order by Last_Name
    """

    # songleaders from the dropdown menu
    cursor.execute(sql_leaders)
    leaders_result = cursor.fetchall()

    leaders_option = ""
    for row in leaders_result:
        first = row[0]
        last = row[1]
        full_name = f"{first} {last}"
        leaders_option += f"<option value='{full_name}'>{full_name}</option>"

    cursor.close()
    con.close()

    # current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return HTML_DETAILS.format(svc_datetime, theme, songleader, event_rows, current_time, leaders_option, service_id)

# Launch the local web server
if __name__ == "__main__":
    app.run(host="localhost", debug=True)
