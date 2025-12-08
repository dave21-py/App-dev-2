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



# Launch the local web server
if __name__ == "__main__":
    app.run(host="localhost", debug=True)
