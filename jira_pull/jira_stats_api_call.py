import requests
import json
import os
from requests.auth import HTTPBasicAuth
from datetime import date
import datetime
import sys


# input, initialization
try:
    board_name = sys.argv[1]
except:
    print("Error: list of boards missing.")
    exit()

nb_days_before = int(1)  # place holder
start_days_ago = 90
headers = {"Accept": "application/json"}

# prep dates
today = datetime.datetime.utcnow().date()
dtoday = today.strftime("%m/%d/%Y")
filename_today = today.strftime("%m-%d-%Y")

# output file cleanup
filename = str(board_name + "_" + filename_today + ".csv")

try:
    os.remove(filename)
except:
    print("(No " + board_name + "results files to delete.)")


def jira_query(board_name, jqlquery, nb_days_before, name):

    # prep, make the API call
    url = (
        "https://datadoghq.atlassian.net/rest/api/3/search?jql="
        + jqlquery
        # + "&maxResults=0"
    )

    auth = HTTPBasicAuth(os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_KEY"))
    response = requests.request("GET", url, headers=headers, auth=auth)

    # error out if response wasn't clean
    if str(response) != "<Response [200]>":
        return print("Error from API: " + str(response) + " for: \n" + jqlquery)

    # prepare to write
    concerneddate = today - datetime.timedelta(days=nb_days_before)
    dconcerneddate = concerneddate.strftime("%m/%d/%Y")
    total = response.json()["total"]
    # print(response.json())

    # max returned issues is 50 - throw a warning if that's the case
    if int(total) >= 50:
        print(
            "\nWarning: Max Issues returned - possible truncation on "
            + str(dconcerneddate)
            + ". Value is "
            + str(total)
        )
    # print(response.json()["total"])
    # print(len(response.json()["issues"]))

    f = open(filename, "a+")
    # f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))
    f.write("%s;%s;%d;%s  \r\n" % (name, dconcerneddate, total, board_name))
    f.close()


print("\nQuerying: " + board_name)

for nb_days_before in range(start_days_ago, -1, -1):

    # Update JQL queries:

    # includes feature requests, if they started in Triage
    # issues now hidden by the DONE column do show up in this count!
    QUERY_CREATED_IN_TRIAGE = (
        "project ="
        + board_name
        + ' and "For Escalation Batter?" =No AND ( status was "T2 TRIAGE"  during (startOfDay(-'
        + str(nb_days_before)
        + ") ,endOfDay(-"
        + str(nb_days_before)
        + ") ) AND  created >= startOfDay(-"
        + str(nb_days_before)
        + ") AND created <= endOfDay(-"
        + str(nb_days_before)
        + ")  )"
    )
    jira_query(board_name, QUERY_CREATED_IN_TRIAGE, nb_days_before, "New Issues")
    # jqlquery = QUERY_CARDS_MOVED_TO_TRIAGE
    # print(nb_days_before)

    # nb_days_before = sys.argv[1]
    # nb_days_before_int = int(nb_days_before)

    percent_done = ((start_days_ago - nb_days_before) / start_days_ago) * 100
    if percent_done % 10 <= 1:
        print(board_name + ": " + str(percent_done) + "% \n", end=" ", flush=True)

print(board_name + " API query complete: " + filename + " finished.")

