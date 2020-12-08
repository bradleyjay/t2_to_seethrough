import requests
import json
import os
from requests.auth import HTTPBasicAuth
from datetime import date, timezone
import datetime
import sys
import copy
from statistics import mean
import numpy as np

# input, initialization
try:
    board_name = sys.argv[1]
    print(board_name)
except:
    print("Error: list of boards missing.")
    exit()

nb_days_before = int(1)  # place holder
start_days_ago = 120  # usually, use 120 here. test at 10.
start_date = datetime.date(2020, 11, 1)

# for lifetime, create proper TZ'd datetime obj. And, set cutoff to 30 days past start date.
start_datetime = datetime.datetime.combine(
    start_date, datetime.datetime.min.time()
).replace(tzinfo=timezone.utc)
cutoff_datetime = start_datetime + datetime.timedelta(days=30)


headers = {"Accept": "application/json"}
ttft_dict = {}
issues_dict = {}
orphans = []

# store by touch date, or card creation date?
ttft_storebytouch = False

# testdump the API response and exit if True
# debug = True
debug = False

# print changelog (lifetime and eng% reports)
print_reports = True
# print_reports = False

# Eng only support board? Check eenginneering triage
# serveerless, security
if board_name in ["SLES", "SCRS", "PRMS", "WEBINT"]:
    target_column = "Engineering Triage"
else:
    target_column = "T2 Triage"

# prep dates
today = datetime.datetime.now(datetime.timezone.utc).date()  # now has tz
dtoday = today.strftime("%m/%d/%Y")
filename_today = today.strftime("%m-%d-%Y")

# output file cleanup
filename = str(board_name + "-count_" + filename_today + ".csv")
testdump_filename = str(board_name + "-testdump.csv")

try:
    os.remove(testdump_filename)
except:
    print("No previous testdump present.")

# flesh out for other boards
if board_name == "AGENT":
    fields_list = ["issuetype", "issue_service", "issue_issue"]
else:
    fields_list = []


def get_field_breakdowns(issue_metadata, issue):
    # take issue, parse for field info, add that to the issue's dict in issue_dict

    issue_metadata["issuetype"] = issue["fields"]["issuetype"]["name"]

    # (Create list of possible values from this?) May need to gate this with only relevant issue types

    # refactor: turn this into a map via dict. No need to have each be a codeblock.
    # "Agent Core"
    if issue_metadata["issuetype"] == "Agent Core":
        if issue["fields"]["customfield_10246"] is not None:
            issue_metadata["issue_service"] = issue["fields"]["customfield_10246"][
                "value"
            ]
        else:
            issue_metadata["issue_service"] = "None"

        if issue["fields"]["customfield_10241"] is not None:
            issue_metadata["issue_issue"] = issue["fields"]["customfield_10241"][
                "value"
            ]
        else:
            issue_metadata["issue_issue"] = "None"

    # "Agent Integrations"
    if issue_metadata["issuetype"] == "Agent Integrations":
        if issue["fields"]["customfield_10247"] is not None:
            issue_metadata["issue_service"] = issue["fields"]["customfield_10247"][
                "value"
            ]
        else:
            issue_metadata["issue_service"] = "None"

        if issue["fields"]["customfield_10241"] is not None:
            issue_metadata["issue_issue"] = issue["fields"]["customfield_10241"][
                "value"
            ]
        else:
            issue_metadata["issue_issue"] = "None"

    # "Integration Tools & Libraries"
    if issue_metadata["issuetype"] == "Integration Tools & Libraries":
        if issue["fields"]["customfield_10255"] is not None:
            issue_metadata["issue_service"] = issue["fields"]["customfield_10255"][
                "value"
            ]
        else:
            issue_metadata["issue_service"] = "None"

        if issue["fields"]["customfield_10241"] is not None:
            issue_metadata["issue_issue"] = issue["fields"]["customfield_10241"][
                "value"
            ]
        else:
            issue_metadata["issue_issue"] = "None"

    # "Agent Platform"
    if issue_metadata["issuetype"] == "Agent Platform":
        # if issue["fields"]["customfield_10255"] is not None:
        # issue_metadata["issue_service"] = issue["fields"]["customfield_10255"][
        #         "value"
        #     ]
        # else:
        issue_metadata[
            "issue_service"
        ] = "None (Agent Platform)"  # every "Agent Platform Service" is null, something's borked SE/Jira-side

        if issue["fields"]["customfield_10241"] is not None:
            issue_metadata["issue_issue"] = issue["fields"]["customfield_10241"][
                "value"
            ]
        else:
            issue_metadata["issue_issue"] = "None"

    # "Infra Integrations"
    if issue_metadata["issuetype"] == "Infrastructure Integrations":
        if issue["fields"]["customfield_10492"] is not None:
            issue_metadata["issue_service"] = issue["fields"]["customfield_10492"][
                "value"
            ]
        else:
            issue_metadata["issue_service"] = "None"

        if issue["fields"]["customfield_10241"] is not None:
            issue_metadata["issue_issue"] = issue["fields"]["customfield_10241"][
                "value"
            ]
        else:
            issue_metadata["issue_issue"] = "None"

    return issue_metadata


def get_and_parse_changelog(issue, auth):
    # make API call to pull changelog for issue

    # Format: "https://datadoghq.atlassian.net/rest/api/3/issue/88682/changelog?expand=changelog"
    url = (
        "https://datadoghq.atlassian.net/rest/api/3/issue/"
        + issue["issue_id"]
        + "/changelog?expand=changelog"
        # + "&maxResults=0"
    )

    changelog_response = requests.request("GET", url, headers=headers, auth=auth).json()

    if debug is True:
        print("\n\n CHANGELOG HERE: \n\n" + str(changelog_response))

    # parse changelog: mark issues as "reached Eng, mark lifetime
    # note: this is from the time it reached done, from the creation date. If issue wasn't yet complete it gets the
    # default "search_date - creation_date", correctly (yeah but why, we don't want this...we want through Nov)
    eng_status = ["Engineering Triage", "In Progress"]
    done_date = 0
    for value in changelog_response["values"]:
        if "items" in value:
            for item in value["items"]:
                if item["field"] == "status":
                    # status is Eng Triage, In Prog? Mark issue as "reached eng"
                    if (
                        item["fromString"] in eng_status
                        or item["toString"] in eng_status
                    ):
                        issue["reached_eng"] = 1

                    # status is Done? Save date. After loop, newest DONE used for lifetime
                    if item["toString"] == "Done":
                        done_date = value[
                            "created"
                        ]  # changelog log creation, i.e. when Done occured
                        if debug is True:
                            print("Done date:" + str(done_date))

    # leave lifetime alone if it never hit Done; default at dict creation
    if done_date != 0:
        # convert done date - 2020-11-09T04:02:34.584-0500

        done_date_obj = datetime.datetime.strptime(done_date, "%Y-%m-%dT%H:%M:%S.%f%z")
        issue["lifetime"] = (done_date_obj - issue["issue_created"]).days

    return issue


def jira_query(board_name, jqlquery, nb_days_before, start_date, name):

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
    concerneddate = start_date - datetime.timedelta(days=nb_days_before)
    dconcerneddate = concerneddate.strftime("%m/%d/%Y")
    total = response.json()["total"]

    # max returned issues is 100 - throw a warning if that's the case
    if int(total) >= 100:
        print(
            "\nWarning: Max Issues returned - possible truncation on "
            + str(dconcerneddate)
            + ". Value is "
            + str(total)
        )

    # debug mode - print raw JSON response to file, appending each day.
    if debug is True:

        f = open(testdump_filename, "a+")
        f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))
        f.close()
        # print("Testdump complete - " + testdump_filename)
        # sys.exit()

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
        try:
            issue_reporter = issue["fields"]["reporter"]["emailAddress"]
        except:
            print("\n\n Trouble here! No issue_reporter \n\n")
            print(issue_key)
            issue_reporter = None
            # continue

        # pull created date. Format: 2020-05-25T21:04:18.666-0400
        raw_issue_created = issue["fields"]["created"]

        # parse to datetime object (includes tz)
        issue_created = datetime.datetime.strptime(
            raw_issue_created, "%Y-%m-%dT%H:%M:%S.%f%z"
        )

        # default lifetime
        default_lifetime = (cutoff_datetime - issue_created).days

        # create dict of dicts: each issue's a dict, then that dict has the following:
        issues_dict[issue_id] = {
            "issue_id": issue_id,
            "issue_reporter": issue_reporter,
            "issue_created": issue_created,
            "issue_key": issue_key,
            "reached_eng": 0,
            "lifetime": default_lifetime,  # update this to issue today - creatoin datee (the max)
        }

        # add fieldbreakdowns (AGENT only, at this time)
        if board_name == "AGENT":
            # print("dict before:" + str(issues_dict[issue_id]))
            issues_dict[issue_id] = get_field_breakdowns(issues_dict[issue_id], issue)
            # print("dict after:" + str(issues_dict[issue_id]))

        # changelog: Get was-eng-hit and lifetime

        issues_dict[issue_id] = get_and_parse_changelog(issues_dict[issue_id], auth)

        #########################################
        ## TTFT SECTION
        ## Parse comments to assess touches
        ## (#REFACTOR)
        #########################################

        # can't check for non-reporer comments without reporter email. Move this lower if
        # we end up using comments for touch count or something, only needed for TTFT

        if issue_reporter is not None:
            # API Call for Comments
            # Format: "https://datadoghq.atlassian.net/rest/api/2/issue/81840/comment"
            url = (
                "https://datadoghq.atlassian.net/rest/api/2/issue/"
                + issue_id
                + "/comment"
                # + "&maxResults=0"
            )

            comments_response = requests.request("GET", url, headers=headers, auth=auth)
            delta_time = None

            for comment in comments_response.json()["comments"]:

                # comments are a LIST, ordered by time
                # iterate til author != issue author
                if comment["author"]["emailAddress"] == issue_reporter:
                    continue

                # take date, parse to simpler date (this'll be our TTFT dict key)
                raw_comment_date = comment["created"]

                # get time delta for (comment created - issue created)
                # includes tz
                comment_date = datetime.datetime.strptime(
                    raw_comment_date, "%Y-%m-%dT%H:%M:%S.%f%z"
                )
                delta_time = (comment_date - issue_created).days

                # if we're storinng TTFT by CREATION DATE, swap the date here now that deltaT is calculated
                if ttft_storebytouch is False:
                    comment_date = issue_created

                # -> append that to dict's value, under TTFT date
                # first check if its there. Yes? Append.
                if str(comment_date.date()) in ttft_dict:

                    ttft_dict[str(comment_date.date())].append((issue_key, delta_time))

                else:

                    ttft_dict[str(comment_date.date())] = [(issue_key, delta_time)]
                    break

            # handling for no comment matching (orphaned case)
            if delta_time == None:
                # theres a LOT of these.... #fixme
                print("\nNo matching comment for issue " + str(issue_key))
                delta_time = (start_date - issue_created.date()).days
                ttft_dict[str(issue_created.date())] = [(issue_key, delta_time)]
                orphans.append([(issue_key, delta_time)])

            # print("TTFT Dict:")
            # print(ttft_dict)

    return ttft_dict
    """
What we have above is a dict (ttft_dict) where the keys are the date of first touch, and the data
is a list of tuples (issue key, the delta between creation date and first comment).

So, at the EoD, avg(bucket) is the TTFT for the day, and count(bucket) is 
how many first touches we had that day.

Later, it might be useful to bucket by CREATION DATE, to say "cards created on this day were touched on 
avg 5 days later". But, LATER

Next steps:

# - note: safety is on -> start_days_ago = 10 on 210 below
- make sure TTFT is getting stored in the dict [x]
- right now, creation date for the card and comments ignores timezone at ingestion. Ingest, make it utc, 
use that date instead. [ x ]
- Write to CSV: After all days have been queried, iterate through possible dates, mapping to a csv output. 
Date, number of first touches, avg time per, max time per. If no first touches that day, 
fill it in, end result should be a spreadsheet of every day, with data for every day. [x]
- general cleanup. there's a lot of variables getting converted, or called with .date() etc, repeatly.

(note that any escalation untouched is ~tossed out, atm. No handling above for a "no comments" or "no comments
by not the requester", around line 154)

    """


def fields_breakdown_report(
    issues_dict, fields_list, board_name, start_date, filename_today, start_days_ago
):

    fields_breakdown = {}

    # populate fields_breakdown with a blank dict for each field
    for field in fields_list:
        fields_breakdown[field] = {}

    issue_count = len(issues_dict)

    # unpack issues: increment count for each field value, nested under the field's name in fields_breakdown
    for issue in issues_dict:
        for field in fields_list:
            # print(issues_dict[issue][field])
            # print(fields_breakdown[field])
            if issues_dict[issue][field] in fields_breakdown[field]:
                fields_breakdown[field][issues_dict[issue][field]] += 1
            else:
                fields_breakdown[field][issues_dict[issue][field]] = 1

    # calculate percentages, dump to csv
    fields_breakdown_pct = copy.deepcopy(fields_breakdown)
    fields_breakdown_name = str(
        board_name + "-fields-report_" + filename_today + ".csv"
    )

    try:
        os.remove(fields_breakdown_name)
    except:
        print("No previous " + board_name + " field breakdown report.")
    f = open(fields_breakdown_name, "a+")

    f.write(
        "%s;%s;%s;%s \r\n"
        % (
            board_name,
            start_date,
            "Prev days incl:" + str(start_days_ago),
            "Total issues:" + str(issue_count),
        )
    )
    f.write("%s;%s;%s;%s \r\n" % ("Field", "Field Value", "Count", "Percentage"))

    for field in fields_breakdown_pct:
        # print(type(field))
        for field_val in fields_breakdown[field]:
            # print(type(field_val))
            fields_breakdown_pct[field][field_val] = round(
                fields_breakdown[field][field_val] / issue_count * 100, 2
            )

            f.write(
                "%s;%s;%f;%.2f \r\n"
                % (
                    field,
                    field_val,
                    fields_breakdown[field][field_val],
                    fields_breakdown_pct[field][field_val],
                )
            )

    f.close()

    # print("\n\n Fields Breakdown Dict: \n" + str(fields_breakdown))
    # print("\n\n Fields Breakdown Pct: \n" + str(fields_breakdown_pct))
    # print(issue_count)


def changelog_reports(
    issues_dict, board_name, start_date, filename_today, start_days_ago
):

    # print report - stats on #, % cards reaching Eng; stats on lifetime
    issue_count = len(issues_dict)

    total_reaching_eng = 0
    lifetime_total = 0
    lifetime_raw = []
    for issue in issues_dict:
        total_reaching_eng += issues_dict[issue]["reached_eng"]
        lifetime_raw.append(issues_dict[issue]["lifetime"])
        lifetime_total += issues_dict[issue]["lifetime"]

    #  reaching eng stats
    pct_reaching_eng = total_reaching_eng / issue_count

    # lifetime stats

    lifetime_values, lifetime_bins = np.histogram(
        lifetime_raw, bins=[0, 3, 7, 10, 14, 17, 21, 24, 28, 35, 42]
    )  # outputs values, bins

    lifetime_stats = {}

    lifetime_stats["lifetime_summed_days"] = lifetime_total
    lifetime_stats["issue_count"] = issue_count
    lifetime_stats["lifetime_average"] = lifetime_total / issue_count
    lifetime_stats["lifetime_p50"] = np.percentile(
        lifetime_raw, 50, interpolation="lower"
    )
    lifetime_stats["lifetime_p75"] = np.percentile(
        lifetime_raw, 75, interpolation="lower"
    )
    lifetime_stats["lifetime_p90"] = np.percentile(
        lifetime_raw, 90, interpolation="lower"
    )
    lifetime_stats["lifetime_p99"] = np.percentile(
        lifetime_raw, 99, interpolation="lower"
    )

    changelog_report = str(board_name + "-changelog-report_" + filename_today + ".csv")

    if debug is True:
        print("lifetime histo:")
        print(lifetime_bins)
        print(lifetime_values)

        print("lifetime_stats")
        print(lifetime_stats)

    try:
        os.remove(changelog_report)
    except:
        print("No previous " + board_name + " changelog report.")
    f = open(changelog_report, "a+")

    f.write(
        "%s;%s;%s;%s;%s \r\n"
        % (
            "ChangeLog report: reached eng, lifetime",
            board_name,
            start_date,
            "Prev days incl:" + str(start_days_ago),
            "Total issues:" + str(issue_count),
        )
    )
    f.write(
        "%s;%s;%d;%s;%d;%s;%.2f \r\n"
        % (
            "\n\nReached Engineering Data",
            "\nCount of Issues Reaching Eng:",
            total_reaching_eng,
            "\nTotal Issues:",
            issue_count,
            "\nPercentage Reaching Eng:",
            pct_reaching_eng,
        )
    )

    f.write("%s \r\n" % ("\n\nLifetime Data"))

    # write stats
    for key, value in lifetime_stats.items():
        f.write("%s;%d \r\n" % (key, value))

    # write histogram
    f.write(
        "%s;%s;%s \r\n"
        % ("\nHistogram: bins are from listed value", "\nBin Value", "Count")
    )
    for i in range(0, len(lifetime_values)):
        f.write("%.2f;%.2f \r\n" % (lifetime_bins[i], lifetime_values[i]))

    f.close()


## Main:

print("\nQuerying: " + board_name)

# start_days_ago = 10
for nb_days_before in range(start_days_ago, -1, -1):

    # set date to search, accounting for date range desired (via start_date)
    # search_date = (today - start_date) + nb_days_before

    # really an Int (today already is a date)
    search_date = (today - start_date).days + nb_days_before
    # Update JQL queries:

    # includes feature requests, if they started in Triage
    # conservative: Escalation Batter won't show, because they'll create then later Batter=No
    # issues now hidden by the DONE column do show up in this count!
    # batter issues could be included by were batter, now aren't, same day. As an aside, there's LOTS of chaff in
    # these boards. Over-filtering is probably good, especially for untouched issues.
    # tl;dr grabs issues created on SEARCHED DATE
    QUERY_CREATED_IN_TRIAGE = (
        "project ="
        + board_name
        + ' and "For Escalation Batter?" =No AND ( status was "'
        + target_column
        + '"  during (startOfDay(-'
        + str(search_date)
        + ") ,endOfDay(-"
        + str(search_date)
        + ") ) AND  created >= startOfDay(-"
        + str(search_date)
        + ") AND created <= endOfDay(-"
        + str(search_date)
        + ")  )"
    )
    ttft_dict = jira_query(
        # tl;dr grabs issues created on SEARCHED DATE -> stores under First Touch date
        board_name,
        QUERY_CREATED_IN_TRIAGE,
        nb_days_before,
        start_date,
        "New Issues",
    )

    # report progress
    percent_done = ((start_days_ago - search_date) / start_days_ago) * 100
    # percent_done =
    #     (1 - ((search_date - (start_date.days) / (start_date.days - start_days_ago).days)
    # )) * 100  # math is right, search date is a number, so need to convert

    if percent_done % 10 <= 1:
        print(board_name + ": " + str(percent_done) + "% \n", end=" ", flush=True)

# unpack TTFL (move all writes here?)
ttft_file = str(board_name + "-ttft_" + filename_today + ".csv")
# write_to_csv(ttft_dict, "TTFT", ttft_file, board_name, start_days_ago, today)

# open file: prepare to write
f = open(ttft_file, "a+")
name = "TTFT"
for nb_days_before in range(start_days_ago, -1, -1):
    # concerneddate = today - datetime.timedelta(days=nb_days_before)
    # this is how we account for offset. slightly different than the above, may want to match later
    concerneddate = start_date - datetime.timedelta(days=nb_days_before)
    target_date = str(concerneddate)

    # if present, pull and unpack
    if target_date in ttft_dict:

        # get (issue key, ttft) pairs:
        points_from_date = ttft_dict[target_date]

        # get count
        ttft_count = len(points_from_date)

    # if not, prepare a zero for stats
    else:
        points_from_date = [("n/a", 0)]

        # set count
        ttft_count = 0

    # extract just the ttft values:
    ttft_values = [point[1] for point in points_from_date]

    # calculate stats:
    ttft_avg = mean(ttft_values)
    ttft_max = max(ttft_values)
    ttft_sum = sum(ttft_values)

    f.write(
        "%s;%s;%s;%d;%d;%d;%d;%s  \r\n"
        % (
            name,
            target_date,
            points_from_date,
            ttft_sum,
            ttft_avg,
            ttft_max,
            ttft_count,
            board_name,
        )
    )

f.close()

f = open("orphans.dat", "a+")
for orphan in orphans:
    f.write(str(orphan) + "\n")

f.close()

print(board_name + " API query complete: " + filename + " finished.")

if debug is True:
    print("\n\n Issues Dict: \n" + str(issues_dict))


# add fieldbreakdowns (AGENT only, at this time)
if print_reports is True:
    if board_name == "AGENT":
        fields_breakdown_report(
            issues_dict,
            fields_list,
            board_name,
            start_date,
            filename_today,
            start_days_ago,
        )

        changelog_reports(
            issues_dict, board_name, start_date, filename_today, start_days_ago
        )


# write_to_csv(ttft_dict, "TTFT", ttft_file, board_name, start_days_ago, today)

# open file: prepare to write


# def write_to_csv(self, data, name, filename, board_name, start_days_ago, today):

#     # write issue count
#     f = open(filename, "a+")

#     for nb_days_before in range(start_days_ago, -1, -1):

#         concerneddate = today - datetime.timedelta(days=nb_days_before)
#         dconcerneddate = concerneddate.strftime("%m/%d/%Y")

#         if dconcerneddate in data:
#             f.write("%s;%s;%d;%s  \r\n" % (name, dconcerneddate, data, board_name))

#         if not print date, 0

#         # f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))

#     f.close()
