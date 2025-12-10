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

# main HTML template for listing services
HTML_MAIN = """
<html>
<head>
    <title>Service Order Generator</title>
</head>
<body>
    <h1>LIST OF SERVICES</h1>
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
</html>
"""

# html template for service details page
HTML_DETAILS = """
<html>
<head>
    <title>Service Details</title>
</head>
<body>
    <h1>SERVICE DETAILS</h1>
    <h2><u>Service Info</u></h2>

    <p><b>Date/Time:</b> {0}</p>
    <p><b>Theme:</b> {1}</p>
    <p><b>Songleader:</b> {2}</p>

    <h2><u>Events</u></h2>
    <table border='1' cellpadding='5' cellspacing='0'>
        <tr>
            <th>Seq</th>
            <th>Type</th>
            <th>Title</th>
            <th>Person</th>
            <th>Notes</th>
        </tr>
        {3}
    </table>
    <br>
    <hr>
    <h2><u>Create New Service</u></h2>
    <form action="/create_service" method="POST">
        <p> (Fields marked with * must be entered)</p>
        <input type="hidden" name="template_id" value="{6}"> 
        <p>
            <label>Date/Time (YYYY-MM-DD HH:MM:SS) *:</label><br>
            <input type="text" name="new_date" value="{4}">
        </p>
        <p>
            <label>Theme:</label><br>
            <input type="text" name="new_theme" value="{1}">
        </p>
        <p>
            <label>Songleader:</label><br>
            <select name="new_songleader">
                <option value="">None</option>
                {5}
            </select>
        </p>
        <input type="submit" value="Create Service">
    </form>
    <br>
    <a href="/">Back to Home Page</a>
</body>
</html>
"""  

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

    # select all the services ordered by most recent
    sql = """
        SELECT Service_ID, Svc_DateTime, Theme_Event
        FROM service
        ORDER BY Svc_DateTime DESC
    """

    cursor.execute(sql)
    result = cursor.fetchall()

    # build table rows for the html page
    table_rows = ""
    for row in result:
        (service_id, svc_datetime, theme) = row

        # handle the null values
        if theme is None:
            theme = ""
        
        # link to details page
        link = f"<a href='/service_details?id={service_id}'>VIEW</a>"

        table_row = f"""
        <tr>
            <td>{svc_datetime}
            <td>{theme}
            <td>{link}
        </tr>
        """
        table_rows += table_row

    # close database resources
    cursor.close()
    con.close()

    # return final formmatted html
    return HTML_MAIN.format(table_rows)

@app.route("/service_details")
def service_details():
    # get service id from url query parameter
    service_id = request.args.get("id")

    # open db connection
    con = connect(
        user=dbconfig.DB_USER,
        password=dbconfig.DB_PASS,
        database=dbconfig.DB_NAME,
        host=dbconfig.DB_HOST,
    )
    cursor = con.cursor()

    # query for service info and songleader
    sql_info = """
        SELECT 
            s.Svc_DateTime,
            s.Theme_Event,
            CONCAT(p.First_Name, ' ', p.Last_Name) AS songleader_name
        FROM service s
        LEFT JOIN fills_role fr 
          ON s.Service_ID = fr.Service_ID AND fr.Role_Type = 'S'
        LEFT JOIN person p 
            ON fr.Person_ID = p.Person_ID
        WHERE s.Service_ID = %s
    """

    cursor.execute(sql_info, (service_id,))
    result = cursor.fetchall()

    # initialise the values
    svc_datetime = ""
    theme = ""
    songleader = ""

    for row in result:
        (svc_datetime, theme, songleader) = row

    if theme is None: theme = ""
    if songleader is None: songleader = "None"  

    # query for servce events
    sql_events = """
        SELECT 
            si.Seq_Num,
            et.Description,
            s.Title,
            si.Title,
            p.First_Name,
            p.Last_Name,
            si.Notes
        FROM service_item si
        JOIN event_type et 
            ON si.Event_Type_ID = et.Event_Type_ID
        LEFT JOIN song s 
            ON si.Song_ID = s.Song_ID
        LEFT JOIN person p 
            ON si.Person_ID = p.Person_ID
        WHERE si.Service_ID = %s
        ORDER BY si.Seq_Num
    """

    cursor.execute(sql_events, (service_id,))
    events_result = cursor.fetchall()

    # build event table rows
    event_rows = ""
    for row in events_result:
        (seq, etype, song_title, item_title, fname, lname, notes) = row
        
        # choose correct title
        display_title = ""
        if song_title:
            display_title = song_title
        elif item_title:
            display_title = item_title

        # format full name
        person_name = ""
        if fname:
            person_name = f"{fname} {lname}"

        if notes is None:
            notes = ""

        # add row
        event_rows += f"""
        <tr>
        <td>{seq}</td>
        <td>{etype}</td>
        <td>{display_title}</td>
        <td>{person_name}</td>
        <td>{notes}</td>
        </tr>
        """

    # query all songleaders for dropdown
    sql_leaders = """
        SELECT DISTINCT 
            First_Name, Last_Name
        FROM person p
        JOIN fills_role fr 
            ON p.Person_ID = fr.Person_ID
        WHERE fr.Role_Type = 'S'
        ORDER BY Last_Name
    """

    cursor.execute(sql_leaders)
    leaders_result = cursor.fetchall()
    
    # dropdown options
    leaders_option = ""
    for row in leaders_result:
        first = row[0]
        last = row[1]
        full_name = f"{first} {last}"
        leaders_option += f"<option value='{full_name}'>{full_name}</option>"

    # close db
    cursor.close()
    con.close()

    # get current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # return final formatted html
    return HTML_DETAILS.format(svc_datetime, theme, songleader, event_rows, current_time, leaders_option, service_id)


@app.route("/create_service", methods=['POST'])
def create_service_action():
    template_id = request.form.get("template_id")
    new_date = request.form.get("new_date")
    new_theme = request.form.get("new_theme")
    new_songleader = request.form.get("new_songleader")

    # prompt if empty date entered
    if not new_date:
        return f"""
        <html><body>
        <h1>ERROR</h1>
        <p>Date/Time is required.</p>
        <p>Please enter a value in the format <b>YYYY-MM-DD HH:MM:SS</b>.</p>
        <p><a href='javascript:history.back()'>Go Back</a></p>
        </body></html>
        """

    # validate date format
    try:
        datetime.strptime(new_date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return f"""
        <html><body>
        <h1>ERROR</h1>
        <p>Invalid date format: {new_date}</p>
        <p>Please use <b>YYYY-MM-DD HH:MM:SS</b></p>
        <p><a href='javascript:history.back()'>Go Back</a></p>
        </body></html>
        """

    # convert empty strings to null
    if not new_theme: new_theme = None
    if not new_songleader: new_songleader = None

    # open db for stored procedure call
    con = connect(
        user=dbconfig.DB_USER,
        password=dbconfig.DB_PASS,
        database=dbconfig.DB_NAME,
        host=dbconfig.DB_HOST,
    )
    cursor = con.cursor()

    # call stored procedure
    args = [template_id, new_date, new_theme, new_songleader, 0] # 0 as placeholder 
    result_args = cursor.callproc('create_service', args)
    result_code = result_args[4]
    con.commit()
    cursor.close()
    con.close()

    # handle duplicate service error
    if result_code == 1:
        return f"""
        <html><body>
        <h1>ERROR</h1>
        <p>SERVICE ALREADY EXISTS AT: {new_date}</p>
        <p><a href='javascript:history.back()'>Go Back</a></p>
        </body></html>
        """
    
    # success message
    else:
        return f"""
        <html><body>
        <h1>SUCCESS</h1>
        <p>NEW SERVICE CREATED!</p>
        <ul>
        <li>Date: {new_date}</li>
        <li>Theme: {new_theme}</li>
        <li>Songleader: {new_songleader}</li>
        </ul>
        <p><a href='/'>RETURN TO THE HOME PAGE</a></p>
        </body></html>
        """


# Launch the local web server
if __name__ == "__main__":
    app.run(host="localhost", debug=True)
