import requests
import json
import os
from requests.auth import HTTPBasicAuth
from datetime import date
import datetime
import sys
import copy


# input, initialization
try:
    board_name = sys.argv[1]
except:
    print("Error: list of boards missing.")
    exit()

nb_days_before = int(1)  # place holder
start_days_ago = 90
headers = {"Accept": "application/json"}
ttft_dict = {}
issues_dict = {}

# prep dates
today = datetime.datetime.utcnow().date()
dtoday = today.strftime("%m/%d/%Y")
filename_today = today.strftime("%m-%d-%Y")

# output file cleanup
filename = str(board_name + "_" + filename_today + ".csv")

try:
    os.remove(filename)
    os.remove(testdump.dat)
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

    # max returned issues is 100 - throw a warning if that's the case
    if int(total) >= 100:
        print(
            "\nWarning: Max Issues returned - possible truncation on "
            + str(dconcerneddate)
            + ". Value is "
            + str(total)
        )
    # print(response.json()["total"])
    # print(len(response.json()["issues"]))

    # debug mode - print raw JSON response to file, appending each day.

    f = open("testdump.dat", "a+")
    f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))
    f.close()

    # write issue count
    f = open(filename, "a+")
    # f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))
    f.write("%s;%s;%d;%s  \r\n" % (name, dconcerneddate, total, board_name))
    f.close()

    # TTFL
    # unpack issues into list: need issue id, created date, creator

    for issue in response.json()["issues"]:
        issue_id = issue["id"]
        issue_key = issue["key"]
        issue_reporter = issue["fields"]["reporter"]["emailAddress"]

        # hacky
        raw_issue_created = issue["fields"]["created"]
        issue_created = datetime.datetime.strptime(
            raw_issue_created.split("T")[0], "%Y-%m-%d"
        )

        issues_dict[issue_id] = {
            "issue_id": issue_id,
            "issue_reporter": issue_reporter,
            "issue_created": issue_created,
            "issue_key": issue_key,
        }

        # test. WORKS!
        # exit()
        # print(issues_dict)

        # API Call for Comments
        url = (
            "https://datadoghq.atlassian.net/rest/api/2/issue/"
            + issue_id
            + "/comment"
            # + "&maxResults=0"
        )

        # "https://datadoghq.atlassian.net/rest/api/2/issue/81840/comment"
        comments_response = requests.request("GET", url, headers=headers, auth=auth)
        # input("Comments Response:")
        # print(comments_response)

        delta_time = None

        for comment in comments_response.json()["comments"]:
            # comments are a LIST, ordered by time
            # print(comment["author"]["emailAddress"])

            # now, do the thing:
            # iterate til author != issue author
            if comment["author"]["emailAddress"] == issue_reporter:
                continue

            # take date, parse to simpler date? (this'll be our TTFT dict key)
            # print(comment["created"])
            raw_comment_date = comment["created"]
            # THIS IGNORES TIMEZONE: get the %z via split or something first, and convert in datetime
            comment_date = datetime.datetime.strptime(
                raw_comment_date.split("T")[0], "%Y-%m-%d"
            )
            # print(comment_date)

            # get time delta for comment created - issue created
            delta_time = (comment_date - issue_created).days
            # print("Delta, in days:")
            # print(delta_time)

            # print(str(issue_created.date()))
            # -> append that to dict's value, under TTFT date
            # first check if its there. Yes? Append.
            if str(comment_date.date()) in ttft_dict:

                print("ttft dict update")
                # ttft_dict[str(issue_created.date())] = ttft_dict[str(issue_created.date())].append(str(issue_created.date()))
                # a = copy.deepcopy(ttft_dict[str(issue_created.date())])
                # a = ttft_dict[str(issue_created.date())]
                # print(type(a))
                # a.append([4])
                ttft_dict[str(comment_date.date())].append((issue_key, delta_time))
                # print(a)
                # .append([4])
                # a None ends up here....how?
                # print(ttft_dict[str(issue_created.date())].type())
                print(ttft_dict)
                break

            else:
                print("First ttft dict")
                ttft_dict[str(comment_date.date())] = [(issue_key, delta_time)]
                print(ttft_dict)
                break
                # str(delta_time)

            # exit()
        # handling for no comment matching
        if delta_time == None:
            print("no matching comment for issue" + str(issue_key))
        print("TTFT Dict:")
        print(ttft_dict)
        pass
        # exit()
    # write ttfl data

    """
What we have above is a dict (ttft_dict) where the keys are the date of first touch, and the data
is a list of tuples (issue key, the delta between creation date and first comment).

So, at the EoD, avg(bucket) is the TTFT for the day, and count(bucket) is how many first touches we had that day.

Later, it might be useful to bucket by CREATION DATE, to say "cards createdd on this day were touched on avg 5 days later". 
But, LATER

Next steps:

- note: safety is on -> start_days_ago = 10 on 210 below
- make sure TTFT is getting stored in the dict [x]
- right now, creation date for the card and comments ignores timezone at ingestion. Ingest, make it utc, use that date instead.
- Write to CSV: After all days have been queried, iterate through possible dates, mapping to a csv output. 
Date, number of first touches, avg time per, max time per. If no first touches that day, 
fill it in, end result should be a spreadsheet of every day, with data for every day.
- general cleanup. there's a lot of variables getting converted, or called with .date() etc, repeatly.

(note that any escalation untouched is ~tossed out, atm. No handling above for a "no comments" or "no comments
by not the requester", around line 154)

    """


print("\nQuerying: " + board_name)

start_days_ago = 10
for nb_days_before in range(start_days_ago, -1, -1):

    # Update JQL queries:

    # includes feature requests, if they started in Triage
    # conservative: Escalation Batter won't show, because they'll create then later Batter=No
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
print(ttft_dict)
