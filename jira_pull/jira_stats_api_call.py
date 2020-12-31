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


##################
### Initalization
##################

### Toggles
# store by touch date, or card creation date?
ttft_storebytouch = False

# testdump the API response if True
# debug = True
debug = False

# print validation for tests
# debug_test = True
debug_test = False

# print changelog (lifetime and eng% reports)
print_reports = True
# print_reports = False


### Reporting window, datetime math

# Set window of time to examine in days. First day chronologically = window_start
reporting_window = 32  # 120 for 3 months (we use a rolling window 30 days in postproc, so need one month extra)
window_end_date = datetime.date(2020, 11, 1)

window_end_datetime = datetime.datetime.combine(
    window_end_date, datetime.datetime.min.time()
).replace(tzinfo=timezone.utc)

window_start_datetime = window_end_datetime - datetime.timedelta(days=reporting_window)
window_start_no_rolling = window_start_datetime + datetime.timedelta(
    days=30
)  # changelog, fields breakdown reports shouldn't include rolling window

# Look forward in time from the window end an additional X days to watch for issue resolution, moving to eng, etc. Impacts changelog, fields breakdown data
lookahead_days = 30  # leave this at 30.
cutoff_datetime = window_end_datetime + datetime.timedelta(days=lookahead_days)

# date math
today = datetime.datetime.now(datetime.timezone.utc).date()  # now has tz
dtoday = today.strftime("%m/%d/%Y")
filename_today = today.strftime("%m-%d-%Y")

### Misc Init
headers = {"Accept": "application/json"}
ttft_dict = {}
issues_dict = {}

# dict for manually sorting bug vs. preventable for D
done_issues_list = []

orphans = []
nb_days_before = int(1)  # init - days counter in main loop

### Board-specific handling
# Eng-only support board? Check enginneering triage (serverless, security)
if board_name in ["SLES", "SCRS", "PRMS", "WEBINT"]:
    target_column = "Engineering Triage"
else:
    target_column = "T2 Triage"

# Fields to check, board-specific
if board_name == "AGENT":
    fields_list = ["issuetype", "issue_service", "issue_issue"]
else:
    fields_list = []

# output file cleanup
filename = str(board_name + "-count_" + filename_today + ".csv")
testdump_filename = str(board_name + "-testdump.csv")


######################
### Helper Functions
######################


def get_field_breakdowns(issue_metadata, issue):
    # take issue, parse for field info, add that to the issue's dict in issue_dict

    issue_metadata["issuetype"] = issue["fields"]["issuetype"]["name"]

    # (Create list of possible values from this?) May need to gate this with only relevant issue types

    # #REFACTOR: turn this into a map via dict. No need to have each be a codeblock.
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
    if "values" in changelog_response:
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

            done_date_obj = datetime.datetime.strptime(
                done_date, "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            issue["lifetime"] = (done_date_obj - issue["issue_created"]).days

    return issue


def calculate_ttft(issue, auth, ttft_dict):

    #########################################
    ## TTFT SECTION
    ## Parse comments to assess touches
    ## (#REFACTOR)
    #########################################

    # can't check for non-reporer comments without reporter email. Move this lower if
    # we end up using comments for touch count or something, only needed for TTFT

    # API Call for Comments
    # Format: "https://datadoghq.atlassian.net/rest/api/2/issue/81840/comment"
    url = (
        "https://datadoghq.atlassian.net/rest/api/2/issue/"
        + issue["issue_id"]
        + "/comment"
        # + "&maxResults=0"
    )

    comments_response = requests.request("GET", url, headers=headers, auth=auth)
    delta_time = None

    if comments_response and "comments" in comments_response.json():
        for comment in comments_response.json()["comments"]:

            # comments are a LIST, ordered by time
            # iterate til author != issue author
            if comment["author"]["emailAddress"] == issue["issue_reporter"]:
                continue

            # take date, parse to simpler date (this'll be our TTFT dict key)
            raw_comment_date = comment["created"]

            # get time delta for (comment created - issue created)
            # includes tz
            comment_date = datetime.datetime.strptime(
                raw_comment_date, "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            delta_time = (comment_date - issue["issue_created"]).days

            # if we're storing TTFT by CREATION DATE, swap the date here now that deltaT is calculated
            if ttft_storebytouch is False:
                comment_date = issue["issue_created"]

            # -> append that to dict's value, under TTFT date
            # first check if its there. Yes? Append.
            if str(comment_date.date()) in ttft_dict:

                ttft_dict[str(comment_date.date())].append(
                    (issue["issue_key"], delta_time)
                )

            else:

                ttft_dict[str(comment_date.date())] = [(issue["issue_key"], delta_time)]
                break

        # handling for no comment matching (orphaned case)
        if delta_time == None:
            # theres a LOT of these.... #fixme
            print("\nNo matching comment for issue " + str(issue["issue_key"]))
            delta_time = (window_end_date - issue["issue_created"].date()).days
            ttft_dict[str(issue["issue_created"].date())] = [
                (issue["issue_key"], delta_time)
            ]
            orphans.append([(issue["issue_key"], delta_time)])

    return ttft_dict

    """
What we have above is a dict (ttft_dict) where the keys are the date of first touch, and the data
is a list of tuples (issue key, the delta between creation date and first comment).

So, at the EoD, avg(bucket) is the TTFT for the day, and count(bucket) is 
how many first touches we had that day.

Later, it might be useful to bucket by CREATION DATE, to say "cards created on this day were touched on 
avg 5 days later". But, LATER

Next steps:

# - note: safety is on -> reporting_window = 10 on 210 below
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


def jira_query(board_name, target_column, search_date, auth):

    # prep, make the API call

    # Update JQL queries:

    # includes feature requests, if they started in Triage
    # conservative: Escalation Batter won't show, because they'll create then later Batter=No
    # issues now hidden by the DONE column do show up in this count!
    # batter issues could be included by were batter, now aren't, same day. As an aside, there's LOTS of chaff in
    # these boards. Over-filtering is probably good, especially for untouched issues.
    # tl;dr grabs issues created on SEARCHED DATE

    jqlquery = (
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

    # build API call URL
    url = (
        "https://datadoghq.atlassian.net/rest/api/3/search?jql="
        + jqlquery
        # + "&maxResults=0"
    )

    api_response = requests.request("GET", url, headers=headers, auth=auth)

    # if debug_test is True:
    #     print("**jira_query**:")
    #     print(board_name, jqlquery, nb_days_before, window_end_date, name)
    #     print("**jira_json**")
    #     print(response.json())
    #     print("\n\n\n\n\n\n")

    # error out if response wasn't clean
    if str(api_response) != "<Response [200]>":
        return print("Error from API: " + str(api_response) + " for: \n" + jqlquery)

    return api_response


# Refactor: new func for unpacking only
def unpack_api_response(
    board_name, nb_days_before, window_end_date, api_response, auth, ttft_dict
):

    """
    First, we'll pull the number of issues as a whole, and write to file.

    Then, we iterate through all issues in the response object. For each one,
    we add it to the issues_dict, contribute to the changelog report, and 
    tag breakdowns, and ttft before moving on to the next issue in the response.

    When complete, we'll have processed every issue created on the current
    iteration's day.

    """

    ################################
    ## Generate Escalations Count ##
    ################################

    concerneddate = window_end_date - datetime.timedelta(days=nb_days_before)
    dconcerneddate = concerneddate.strftime("%m/%d/%Y")
    total = api_response.json()["total"]

    # max returned issues is 100 - throw a warning if that's the case
    if int(total) >= 100:
        print(
            "\nWarning: Max Issues returned - possible truncation on "
            + str(dconcerneddate)
            + ". Value is "
            + str(total)
        )

    # write issue count to file
    f = open(filename, "a+")
    name = "New Issues"  # Refactor: this used to get passed, but only used here. There's a global name, that's for another report, and assigned directly at write time.
    f.write("%s;%s;%d;%s  \r\n" % (name, dconcerneddate, total, board_name))
    f.close()

    ###########################
    ### Prepare issues_dict ###
    ###########################

    # unpack issues into list: need issue id, created date, creator

    for issue in api_response.json()["issues"]:
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

        # actually create issues_dict
        # dict of dicts: each issue's a dict, then that dict has the following:
        issues_dict[issue_id] = {
            "issue_id": issue_id,
            "issue_reporter": issue_reporter,
            "issue_created": issue_created,
            "issue_key": issue_key,
            "reached_eng": 0,
            "lifetime": default_lifetime,  # update this to issue today - creatoin datee (the max)
        }

        ################################################
        ## Add to Field Breakdowns, Changelog reports ##
        ################################################

        if issue_reporter is not None:
            ttft_dict = calculate_ttft(issues_dict[issue_id], auth, ttft_dict)

        # add fieldbreakdowns (AGENT only, at this time)
        if board_name == "AGENT":
            # print("dict before:" + str(issues_dict[issue_id]))
            issues_dict[issue_id] = get_field_breakdowns(issues_dict[issue_id], issue)
            # print("dict after:" + str(issues_dict[issue_id]))

        # changelog: Get was-eng-hit and lifetime

        issues_dict[issue_id] = get_and_parse_changelog(issues_dict[issue_id], auth)
        if (
            issues_dict[issue_id]["lifetime"]
            != default_lifetime
            #
        ):
            done_issues_list.append(issues_dict[issue_id])

    if debug_test is True:
        # issues dict, just for testing

        print("**issues_dict**")
        print(issues_dict)

    return issues_dict


def fields_breakdown_report(
    issues_dict,
    fields_list,
    board_name,
    window_end_date,
    filename_today,
    reporting_window,
):
    ## for testing
    if debug_test is True:
        print("**fields_breakdown_report**")
        print(
            issues_dict,
            fields_list,
            board_name,
            window_end_date,
            filename_today,
            reporting_window,
        )

    fields_breakdown = {}

    # populate fields_breakdown with a blank dict for each field
    for field in fields_list:
        fields_breakdown[field] = {}

    breakdown_count = 0  # refactor. lifetime count = lifetime count. This gating could happen once, filter the list for only issues not using rolling window. Could filter list, pass that to both changelog and breakdown
    # init for issuetype -> service mapping
    service_by_issues = {}

    # unpack issues: increment count for each field value, nested under the field's name in fields_breakdown
    # only take stats for issues in prime 3 months (no rolling window)
    for issue in issues_dict:
        if (
            issues_dict[issue]["issue_created"] > window_start_no_rolling
        ):  # ignore the "rolling window" first 30 days
            breakdown_count += 1
            for field in fields_list:
                # print(issues_dict[issue][field])
                # print(fields_breakdown[field])
                if issues_dict[issue][field] in fields_breakdown[field]:
                    fields_breakdown[field][issues_dict[issue][field]] += 1
                else:
                    fields_breakdown[field][issues_dict[issue][field]] = 1
                if field == "issue_service":

                    _issue_type = issues_dict[issue]["issuetype"]
                    _issue_service = issues_dict[issue]["issue_service"]

                    if _issue_type in service_by_issues:
                        if _issue_service in service_by_issues[_issue_type]:
                            service_by_issues[_issue_type][_issue_service] += 1

                        else:
                            service_by_issues[_issue_type][_issue_service] = 1

                    else:
                        service_by_issues[_issue_type] = {_issue_service: 1}

    # print(service_by_issues)
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
            window_end_date,
            "Prev days incl:" + str(reporting_window),
            "Total issues:" + str(breakdown_count),
        )
    )
    f.write("\n%s;%s;%s;%s \r\n" % ("Field", "Field Value", "Count", "Percentage"))

    for field in fields_breakdown_pct:
        # print(type(field))
        for field_val in fields_breakdown[field]:
            # print(type(field_val))
            fields_breakdown_pct[field][field_val] = round(
                fields_breakdown[field][field_val] / breakdown_count * 100, 2
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

    f.write(
        "\n\n\n%s;%s;%s;%s \r\n"
        % ("Issuetype", "Service", "Count", "Percentage of Issuetype")
    )

    for issuetype in service_by_issues:
        # print(type(field))
        for service in service_by_issues[issuetype]:
            percentage_s = (
                service_by_issues[issuetype][service]
                / sum(service_by_issues[issuetype].values())
                * 100
            )

            f.write(
                "%s;%s;%d;%.2f \r\n"
                % (
                    issuetype,
                    service,
                    service_by_issues[issuetype][service],
                    percentage_s,
                )
            )

    f.close()

    if debug_test is True:
        print("**fields_breakdown**")
        print(fields_breakdown)
        print("\n\n**fields_breakdown_pct**")
        print(fields_breakdown_pct)
        print("\n\n**service_by_issues**")
        print(service_by_issues)

    return fields_breakdown, fields_breakdown_pct, service_by_issues


def changelog_reports(
    issues_dict,
    board_name,
    window_end_date,
    filename_today,
    reporting_window,
    done_issues_list,
):
    if debug_test is True:
        print("**changelog_reports**")
        print(
            issues_dict,
            board_name,
            window_end_date,
            filename_today,
            reporting_window,
            done_issues_list,
        )

    # print report - stats on #, % cards reaching Eng; stats on lifetime
    lifetime_count = 0

    total_reaching_eng = 0
    lifetime_total = 0
    lifetime_raw = []
    for issue in issues_dict:
        # only take stats for issues in prime 3 months (no rolling window)
        if issues_dict[issue]["issue_created"] > window_start_no_rolling:
            lifetime_count += 1
            total_reaching_eng += issues_dict[issue]["reached_eng"]
            lifetime_raw.append(issues_dict[issue]["lifetime"])
            lifetime_total += issues_dict[issue]["lifetime"]

    if len(lifetime_raw) == 0:
        return print(
            "Warning: Lifetime reporting aborted - no Issues present outside of rolling window."
        )
    #  reaching eng stats
    pct_reaching_eng = total_reaching_eng / lifetime_count

    # lifetime stats

    lifetime_values, lifetime_bins = np.histogram(
        lifetime_raw,
        bins=[
            0,
            3,
            7,
            10,
            14,
            17,
            21,
            24,
            28,
            35,
            42,
            150
            # fixme int(reporting_window + lookahead_days),
        ],
    )  # outputs values, bins. # NOTE: histogram chopped at last bin value. MUST use large final value here.

    lifetime_stats = {}

    lifetime_stats["lifetime_summed_days"] = lifetime_total
    lifetime_stats["lifetime_count"] = lifetime_count
    lifetime_stats["lifetime_average"] = lifetime_total / lifetime_count
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
            window_end_date,
            "Prev days incl:" + str(reporting_window),
            "Total issues:" + str(lifetime_count),
        )
    )
    f.write(
        "%s;%s;%d;%s;%d;%s;%.2f \r\n"
        % (
            "\n\nReached Engineering Data",
            "\nCount of Issues Reaching Eng:",
            total_reaching_eng,
            "\nTotal Issues:",
            lifetime_count,
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

    # done_issues_list -> links for manual sorting

    done_issues_report = str(
        board_name + "-done-issues-report_" + filename_today + ".csv"
    )
    try:
        os.remove(done_issues_report)
    except:
        print("No previous " + board_name + " changelog report.")

    f = open(done_issues_report, "a+")

    f.write(
        "%s;%s;%s;%s;%s;%s;%s \r\n"
        % (
            "Issue Key",
            "Creation Date",
            "Issue Type",
            "Issue Service",
            "Issue",
            "Link",
            "Bug, Config Err, Human Err, Poor Docs?",
        )
    )
    for issue in done_issues_list:
        f.write(
            "%s;%s;%s;%s;%s;%s  \r\n"
            % (
                issue["issue_key"],
                issue["issue_created"],
                issue["issuetype"],
                issue["issue_service"],
                issue["issue_issue"],
                str("https://datadoghq.atlassian.net/browse/")
                + str(issue["issue_key"]),
            )
        )
    f.close()

    if debug_test is True:
        print("**lifetime_stats**")
        print(lifetime_stats)
    return lifetime_stats


## Main:

if __name__ == "__main__":

    # cleanup testdump
    try:
        os.remove(testdump_filename)
    except:
        print("No previous testdump present.")

    print("\nQuerying: " + board_name)

    auth = HTTPBasicAuth(os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_KEY"))

    # reporting_window = 10
    for nb_days_before in range(reporting_window, -1, -1):

        # set date to search, accounting for date range desired (via window_end_date)
        # search_date = (today - window_end_date) + nb_days_before

        # really an Int (today already is a date)
        search_date = (today - window_end_date).days + nb_days_before

        api_response = jira_query(
            # tl;dr grabs issues created on SEARCHED DATE -> stores under First Touch date
            board_name,
            target_column,
            search_date,
            auth,
        )

        # used to pass NAME to jira_qurey, used in print stp. why? it was "New Issues"
        # what goes to and from this?
        issues_dict = unpack_api_response(
            board_name, nb_days_before, window_end_date, api_response, auth, ttft_dict
        )

        # debug mode - print raw JSON response to file, appending each day.
        if debug is True:
            f = open(testdump_filename, "a+")
            f.write(json.dumps(api_response.json(), indent=4, separators=(",", ": ")))
            f.close()

        # report progress to command line
        percent_done = ((reporting_window - search_date) / reporting_window) * 100
        # percent_done =
        #     (1 - ((search_date - (window_end_date.days) / (window_end_date.days - reporting_window).days)
        # )) * 100  # math is right, search date is a number, so need to convert

        if percent_done % 10 <= 1:
            print(board_name + ": " + str(percent_done) + "% \n", end=" ", flush=True)

    # unpack TTFL (move all writes here?)
    ttft_file = str(board_name + "-ttft_" + filename_today + ".csv")
    # write_to_csv(ttft_dict, "TTFT", ttft_file, board_name, reporting_window, today)

    # open file: prepare to write
    f = open(ttft_file, "a+")
    name = "TTFT"
    for nb_days_before in range(reporting_window, -1, -1):
        # concerneddate = today - datetime.timedelta(days=nb_days_before)
        # this is how we account for offset. slightly different than the above, may want to match later
        concerneddate = window_end_date - datetime.timedelta(days=nb_days_before)
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
                window_end_date,
                filename_today,
                reporting_window,
            )

            changelog_reports(
                issues_dict,
                board_name,
                window_end_date,
                filename_today,
                reporting_window,
                done_issues_list,
            )

