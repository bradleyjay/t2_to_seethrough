import unittest
import datetime
from datetime import date, timezone
from unittest import mock

from jira_stats_api_call import (
    fields_breakdown_report,
    changelog_reports,
    jira_query,
    unpack_api_response,
)


class TestJiraPull(unittest.TestCase):

    # input variables for each function
    issues_dict = {
        "153075": {
            "issue_id": "153075",
            "issue_reporter": "rachel.rath@datadoghq.com",
            "issue_created": datetime.datetime(
                2020,
                10,
                30,
                18,
                33,
                10,
                871000,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
            ),
            "issue_key": "AGENT-5272",
            "reached_eng": 0,
            "lifetime": 4,
            "issuetype": "Agent Core",
            "issue_service": "Linux",
            "issue_issue": "Logging",
        },
        "152821": {
            "issue_id": "152821",
            "issue_reporter": "khang.truong@datadoghq.com",
            "issue_created": datetime.datetime(
                2020,
                10,
                30,
                9,
                55,
                6,
                645000,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
            ),
            "issue_key": "AGENT-5269",
            "reached_eng": 0,
            "lifetime": 11,
            "issuetype": "Agent Integrations",
            "issue_service": "Cisco ACI",
            "issue_issue": "Missing Data",
        },
        "153163": {
            "issue_id": "153163",
            "issue_reporter": "dalen.leung@datadoghq.com",
            "issue_created": datetime.datetime(
                2020,
                11,
                1,
                23,
                37,
                26,
                815000,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400)),
            ),
            "issue_key": "AGENT-5273",
            "reached_eng": 0,
            "lifetime": 28,
            "issuetype": "Agent Integrations",
            "issue_service": "Jboss Wildfly",
            "issue_issue": "Metrics",
        },
    }
    fields_list, board_name, start_date, filename_today, start_days_ago = (
        ["issuetype", "issue_service", "issue_issue"],
        "AGENT",
        datetime.date(2020, 11, 1),
        "12-17-2020",
        "2",
    )
    done_issues_list = [
        {
            "issue_id": "153075",
            "issue_reporter": "rachel.rath@datadoghq.com",
            "issue_created": datetime.datetime(
                2020,
                10,
                30,
                18,
                33,
                10,
                871000,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
            ),
            "issue_key": "AGENT-5272",
            "reached_eng": 0,
            "lifetime": 4,
            "issuetype": "Agent Core",
            "issue_service": "Linux",
            "issue_issue": "Logging",
        },
        {
            "issue_id": "152821",
            "issue_reporter": "khang.truong@datadoghq.com",
            "issue_created": datetime.datetime(
                2020,
                10,
                30,
                9,
                55,
                6,
                645000,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
            ),
            "issue_key": "AGENT-5269",
            "reached_eng": 0,
            "lifetime": 11,
            "issuetype": "Agent Integrations",
            "issue_service": "Cisco ACI",
            "issue_issue": "Missing Data",
        },
    ]
    jqlquery, nb_days_before, name = (
        'project =AGENT and "For Escalation Batter?" =No AND ( status was "T2 Triage"  during (startOfDay(-48) ,endOfDay(-48) ) AND  created >= startOfDay(-48) AND created <= endOfDay(-48)  )',
        int(2),
        "New Issues",
    )
    board_name = "AGENT"
    target_column = "T2 Triage"
    search_date = 48
    window_end_date = datetime.date(2020, 11, 1)
    auth = 4  # placeholder, mocking the API call anyway so it doesn't matter

    def test_fields_breakdown_report(self):
        (
            fields_breakdown,
            fields_breakdown_pct,
            service_by_issues,
        ) = fields_breakdown_report(
            self.issues_dict,
            self.fields_list,
            self.board_name,
            self.start_date,
            self.filename_today,
            self.start_days_ago,
        )

        # "correct" values
        cfields_breakdown = {
            "issuetype": {"Agent Core": 1, "Agent Integrations": 2},
            "issue_service": {"Linux": 1, "Cisco ACI": 1, "Jboss Wildfly": 1},
            "issue_issue": {"Logging": 1, "Missing Data": 1, "Metrics": 1},
        }
        cfields_breakdown_pct = {
            "issuetype": {"Agent Core": 33.33, "Agent Integrations": 66.67},
            "issue_service": {
                "Linux": 33.33,
                "Cisco ACI": 33.33,
                "Jboss Wildfly": 33.33,
            },
            "issue_issue": {"Logging": 33.33, "Missing Data": 33.33, "Metrics": 33.33},
        }
        cservice_by_issues = {
            "Agent Core": {"Linux": 1},
            "Agent Integrations": {"Cisco ACI": 1, "Jboss Wildfly": 1},
        }

        self.assertEqual(
            (fields_breakdown, fields_breakdown_pct, service_by_issues),
            (cfields_breakdown, cfields_breakdown_pct, cservice_by_issues),
        )
        # changelog
        ## **changelog_reports** -> args for changelog ['issuetype', 'issue_service', 'issue_issue'] AGENT 2020-11-01 12-17-2020 90
        # issues_dict, fields_list, board_name, start_date, filename_today, start_days_ago
        # changelog_report(
        #     issues_dict, fields_list, board_name, start_date, filename_today, start_days_ago
        # )

    def test_changelog(self):
        lifetime_stats = changelog_reports(
            self.issues_dict,
            self.board_name,
            self.start_date,
            self.filename_today,
            self.start_days_ago,
            self.done_issues_list,
        )

        # "correct" values
        clifetime_stats = {
            "lifetime_summed_days": 43,
            "lifetime_count": 3,
            "lifetime_average": 14.333333333333334,
            "lifetime_p50": 11,
            "lifetime_p75": 11,
            "lifetime_p90": 11,
            "lifetime_p99": 11,
        }

        self.assertEqual(clifetime_stats, lifetime_stats)

    def mocked_api_response(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.json_data = {
                    "expand": "schema,names",
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 2,
                    "issues": [
                        {
                            "expand": "operations,versionedRepresentations,editmeta,changelog,renderedFields",
                            "id": "153075",
                            "self": "https://datadoghq.atlassian.net/rest/api/3/issue/153075",
                            "key": "AGENT-5272",
                            "fields": {
                                "resolution": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/resolution/10000",
                                    "id": "10000",
                                    "description": "Work has been completed on this issue.",
                                    "name": "Done",
                                },
                                "lastViewed": None,
                                "customfield_10183": None,
                                "customfield_10184": None,
                                "customfield_10185": None,
                                "labels": ["jira_escalated"],
                                "aggregatetimeoriginalestimate": None,
                                "issuelinks": [],
                                "assignee": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/user?accountId=5d4b4767a23f060c108396b2",
                                    "accountId": "5d4b4767a23f060c108396b2",
                                    "emailAddress": "laura.hampton@datadoghq.com",
                                    "avatarUrls": {
                                        "48x48": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/5d4b4767a23f060c108396b2/c5daf7ab-1b75-4ee8-b5ab-ee3ec9055824/48",
                                        "24x24": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/5d4b4767a23f060c108396b2/c5daf7ab-1b75-4ee8-b5ab-ee3ec9055824/24",
                                        "16x16": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/5d4b4767a23f060c108396b2/c5daf7ab-1b75-4ee8-b5ab-ee3ec9055824/16",
                                        "32x32": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/5d4b4767a23f060c108396b2/c5daf7ab-1b75-4ee8-b5ab-ee3ec9055824/32",
                                    },
                                    "displayName": "Laura Hampton",
                                    "active": True,
                                    "timeZone": "America/New_York",
                                    "accountType": "atlassian",
                                },
                                "components": [],
                                "customfield_10290": None,
                                "customfield_10291": None,
                                "customfield_10292": None,
                                "customfield_10293": None,
                                "customfield_10294": None,
                                "customfield_10295": None,
                                "customfield_10296": None,
                                "customfield_10297": None,
                                "customfield_10298": None,
                                "customfield_10299": None,
                                "subtasks": [],
                                "customfield_10280": None,
                                "customfield_10281": None,
                                "customfield_10282": None,
                                "customfield_10283": None,
                                "customfield_10284": None,
                                "customfield_10163": None,
                                "reporter": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/user?accountId=70121%3Aacea2b80-3452-441a-9be0-269dbdf6e036",
                                    "accountId": "70121:acea2b80-3452-441a-9be0-269dbdf6e036",
                                    "emailAddress": "rachel.rath@datadoghq.com",
                                    "avatarUrls": {
                                        "48x48": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/70121:acea2b80-3452-441a-9be0-269dbdf6e036/5215ded2-ae52-4662-84c4-e79a3c36ebda/48",
                                        "24x24": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/70121:acea2b80-3452-441a-9be0-269dbdf6e036/5215ded2-ae52-4662-84c4-e79a3c36ebda/24",
                                        "16x16": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/70121:acea2b80-3452-441a-9be0-269dbdf6e036/5215ded2-ae52-4662-84c4-e79a3c36ebda/16",
                                        "32x32": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/70121:acea2b80-3452-441a-9be0-269dbdf6e036/5215ded2-ae52-4662-84c4-e79a3c36ebda/32",
                                    },
                                    "displayName": "Rachel Rath",
                                    "active": True,
                                    "timeZone": "America/New_York",
                                    "accountType": "atlassian",
                                },
                                "customfield_10164": None,
                                "customfield_10285": None,
                                "customfield_10286": None,
                                "customfield_10165": None,
                                "customfield_10287": None,
                                "customfield_10288": None,
                                "customfield_10289": None,
                                "customfield_10710": None,
                                "customfield_10711": None,
                                "customfield_10712": None,
                                "customfield_10713": None,
                                "customfield_10714": None,
                                "customfield_10715": None,
                                "customfield_10716": None,
                                "progress": {"progress": 0, "total": 0},
                                "votes": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issue/AGENT-5272/votes",
                                    "votes": 0,
                                    "hasVoted": False,
                                },
                                "issuetype": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issuetype/11622",
                                    "id": "11622",
                                    "description": "",
                                    "iconUrl": "https://datadoghq.atlassian.net/secure/viewavatar?size=medium&avatarId=10308&avatarType=issuetype",
                                    "name": "Agent Core",
                                    "subtask": False,
                                    "avatarId": 10308,
                                },
                                "customfield_10390": None,
                                "customfield_10391": None,
                                "customfield_10270": None,
                                "customfield_10392": None,
                                "customfield_10271": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "n/a"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10272": "n/a",
                                "customfield_10393": None,
                                "customfield_10394": None,
                                "project": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/project/10435",
                                    "id": "10435",
                                    "key": "AGENT",
                                    "name": "Support - Agent",
                                    "projectTypeKey": "software",
                                    "simplified": False,
                                    "avatarUrls": {
                                        "48x48": "https://datadoghq.atlassian.net/secure/projectavatar?pid=10435&avatarId=10424",
                                        "24x24": "https://datadoghq.atlassian.net/secure/projectavatar?size=small&s=small&pid=10435&avatarId=10424",
                                        "16x16": "https://datadoghq.atlassian.net/secure/projectavatar?size=xsmall&s=xsmall&pid=10435&avatarId=10424",
                                        "32x32": "https://datadoghq.atlassian.net/secure/projectavatar?size=medium&s=medium&pid=10435&avatarId=10424",
                                    },
                                },
                                "customfield_10273": None,
                                "customfield_10274": None,
                                "customfield_10275": None,
                                "customfield_10276": None,
                                "customfield_10277": None,
                                "customfield_10278": None,
                                "customfield_10279": None,
                                "customfield_10269": None,
                                "customfield_10027": None,
                                "customfield_10149": None,
                                "resolutiondate": "2020-11-03T18:22:06.422-0500",
                                "watches": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issue/AGENT-5272/watchers",
                                    "watchCount": 3,
                                    "isWatching": False,
                                },
                                "customfield_10380": None,
                                "customfield_10381": None,
                                "customfield_10260": None,
                                "customfield_10261": None,
                                "customfield_10382": None,
                                "customfield_10020": None,
                                "customfield_10262": "6.23.1",
                                "customfield_10383": None,
                                "customfield_10384": None,
                                "customfield_10263": None,
                                "customfield_10021": None,
                                "customfield_10385": None,
                                "customfield_10022": "2020-10-30T20:56:06.159-0400",
                                "customfield_10023": "11887_*:*_2_*:*_330721046_*|*_11886_*:*_2_*:*_13421971",
                                "customfield_10386": None,
                                "customfield_10265": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://datadog.zendesk.com/attachments/token/fanFz5viOTROZzrOLVqEyxKMn/?name=datadog-agent-2020-10-29-20-31-23.zip",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/fanFz5viOTROZzrOLVqEyxKMn/?name=datadog-agent-2020-10-29-20-31-23.zip"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10387": None,
                                "customfield_10388": None,
                                "customfield_10267": None,
                                "customfield_10389": None,
                                "customfield_10268": None,
                                "customfield_10258": None,
                                "customfield_10016": None,
                                "customfield_10379": None,
                                "customfield_10259": None,
                                "customfield_10017": None,
                                "customfield_10018": {
                                    "hasEpicLinkFieldDependency": False,
                                    "showField": False,
                                    "nonEditableReason": {
                                        "reason": "PLUGIN_LICENSE_ERROR",
                                        "message": "The Parent Link is only available to Jira Premium users.",
                                    },
                                },
                                "customfield_10019": "2|i003af:",
                                "updated": "2020-11-03T18:22:09.948-0500",
                                "customfield_10490": None,
                                "customfield_10491": None,
                                "customfield_10370": None,
                                "timeoriginalestimate": None,
                                "customfield_10250": None,
                                "customfield_10371": None,
                                "customfield_10492": None,
                                "customfield_10372": None,
                                "description": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Customer has a RedHat 7 machine that they recently upgraded to Agent ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "6.23.1",
                                                    "marks": [{"type": "code"}],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": " for testing purposes. When they start the agent with ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "systemctl start datadog-agent",
                                                    "marks": [{"type": "code"}],
                                                },
                                                {"type": "text", "text": " (the "},
                                                {
                                                    "type": "text",
                                                    "text": "standard command",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://docs.datadoghq.com/agent/basic_agent_usage/redhat/?tab=agentv6v7#overview"
                                                            },
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": " for RedHat) the log agent does not work, but when they use ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "datadog-agent start",
                                                    "marks": [{"type": "code"}],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": " the log agent works and posts logs. This also causes the terminal to start a live agent log and when the customer closes it, the log agent stops.",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "They did not have the agent installed on this machine previously. They do the installations via Ansible and they recently upgraded their .rpm from ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "6.10",
                                                    "marks": [{"type": "code"}],
                                                },
                                                {"type": "text", "text": " to "},
                                                {
                                                    "type": "text",
                                                    "text": "6.23.1",
                                                    "marks": [{"type": "code"}],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": " and were testing on a dev machine for the first time with the upgraded agent version.",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "After going to Office Hours, I requested the customer:",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "orderedList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Stop everything related to Datadog",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Run ",
                                                                },
                                                                {
                                                                    "type": "text",
                                                                    "text": "ps -aux",
                                                                    "marks": [
                                                                        {"type": "code"}
                                                                    ],
                                                                },
                                                                {
                                                                    "type": "text",
                                                                    "text": " to confirm no Datadog agents are running",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Start the agent using ",
                                                                },
                                                                {
                                                                    "type": "text",
                                                                    "text": "sudo systemctl start datadog-agent}}\u200b (please make sure to include {{sudo",
                                                                    "marks": [
                                                                        {"type": "code"}
                                                                    ],
                                                                },
                                                                {
                                                                    "type": "text",
                                                                    "text": ")",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Take a screenshot of the results (showing that the log agent does not work)",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "The customer followed the instructions and sent the following screenshots. They say:",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "blockquote",
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "This first screen-capture is the agent status page after starting the agent this way and we can see that no log files are being tailed.",
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "mediaSingle",
                                            "attrs": {"layout": "center"},
                                            "content": [
                                                {
                                                    "type": "media",
                                                    "attrs": {
                                                        "id": "650919e2-66f3-4087-9a18-552b9f168ec7",
                                                        "type": "file",
                                                        "collection": "jira-153075-field-description",
                                                        "width": 1612,
                                                        "height": 512,
                                                        "occurrenceKey": "05dbcc7f-e450-4680-8f03-08df747852b1",
                                                    },
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/xQuAQQdB",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/xQuAQQdB"
                                                            },
                                                        }
                                                    ],
                                                },
                                                {"type": "text", "text": " "},
                                            ],
                                        },
                                        {
                                            "type": "blockquote",
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "This second screen-capture is after stopping the agent again and then starting it using ‘sudo datadog-agent start’. Here the status for logs agent shows the log files being tailed. There only difference between these two outcomes is the command used to start the agent. The problem with using ‘sudo datadog-agent start’ is that the terminal becomes a live agent log and when the ssh session is closed the log agent stops working.",
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "mediaSingle",
                                            "attrs": {"layout": "center"},
                                            "content": [
                                                {
                                                    "type": "media",
                                                    "attrs": {
                                                        "id": "13bbbe81-fcd7-4d8c-b0b4-981bc7e2860b",
                                                        "type": "file",
                                                        "collection": "jira-153075-field-description",
                                                        "width": 2010,
                                                        "height": 918,
                                                        "occurrenceKey": "fab65ff5-3e7f-4400-a87f-8d74f425378a",
                                                    },
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/qGuvBB1Z",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/qGuvBB1Z"
                                                            },
                                                        }
                                                    ],
                                                },
                                                {"type": "text", "text": " "},
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Are there any reasons the standard RedHat commands are not working for this customer?",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "heading",
                                            "attrs": {"level": 3},
                                            "content": [
                                                {"type": "text", "text": "Attachments"}
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "image003.png",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/NRRkQPqoke2yFUDscKkYne8EA/?name=image003.png"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "image004.png",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/vIxdqMBLXMSICZUtrQk61k6QJ/?name=image004.png"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "datadog-agent-2020-10-29-20-31-23.zip",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/fanFz5viOTROZzrOLVqEyxKMn/?name=datadog-agent-2020-10-29-20-31-23.zip"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "datadog-agent-2020-10-29-17-03-37.zip",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/DNqxwLVL3oZZZQK2syEBIwfRw/?name=datadog-agent-2020-10-29-17-03-37.zip"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Please see Zendesk Support tab for further comments and attachments.",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10251": None,
                                "customfield_10252": None,
                                "customfield_10010": None,
                                "customfield_10373": None,
                                "customfield_10253": None,
                                "customfield_10374": None,
                                "customfield_10254": None,
                                "customfield_10375": None,
                                "customfield_10133": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Postmortem processes can be found here:  ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://docs.google.com/document/d/1Jon66NB-QsOqAI9E2T9OgjlZIKwN_zuKPL9oOV4Xf_8/edit",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://docs.google.com/document/d/1Jon66NB-QsOqAI9E2T9OgjlZIKwN_zuKPL9oOV4Xf_8/edit"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "1. Remember to set a due date 5 working days forward on the card",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "2. Remember to add the appropriate Engineering Director and VP to the card",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "3. Add the internal and public postmortems as attachments",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "4. Drop them in the Engineering shared drive (under postmortems)",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Please add the following information here: ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Organization(s) Requesting",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Date and Time of Outage",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Link to Slack Channel and Link to Incident App",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Zendesk ticket(s) ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Additional Notes/Requests",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "The original Trello URL is ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "https://trello.com/c/hBSVjH3Y/115-template-card",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://trello.com/c/hBSVjH3Y/115-template-card"
                                                            },
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10255": None,
                                "customfield_10376": None,
                                "customfield_10256": None,
                                "customfield_10377": None,
                                "customfield_10014": None,
                                "customfield_10015": None,
                                "customfield_10378": None,
                                "customfield_10257": None,
                                "customfield_10247": None,
                                "customfield_10368": None,
                                "customfield_10005": None,
                                "customfield_10006": None,
                                "customfield_10248": None,
                                "customfield_10369": None,
                                "customfield_10007": None,
                                "customfield_10249": None,
                                "customfield_10008": None,
                                "customfield_10009": None,
                                "summary": "Standard RedHat 7 commands do not start the log agent",
                                "customfield_10480": None,
                                "customfield_10481": None,
                                "customfield_10360": None,
                                "customfield_10240": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10304",
                                    "value": "No",
                                    "id": "10304",
                                },
                                "customfield_10361": None,
                                "customfield_10482": None,
                                "customfield_10483": None,
                                "customfield_10362": None,
                                "customfield_10241": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10321",
                                    "value": "Logging",
                                    "id": "10321",
                                },
                                "customfield_10363": None,
                                "customfield_10242": "Logs Agent",
                                "customfield_10000": "{}",
                                "customfield_10243": None,
                                "customfield_10001": None,
                                "customfield_10364": None,
                                "customfield_10365": None,
                                "customfield_10002": None,
                                "customfield_10244": None,
                                "customfield_10003": None,
                                "customfield_10245": None,
                                "customfield_10004": None,
                                "customfield_10367": None,
                                "customfield_10246": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10367",
                                    "value": "Linux",
                                    "id": "10367",
                                },
                                "customfield_10478": None,
                                "customfield_10236": "1272098",
                                "customfield_10357": None,
                                "customfield_10237": "trta-onesource",
                                "customfield_10479": None,
                                "customfield_10358": None,
                                "customfield_10359": None,
                                "environment": None,
                                "customfield_10238": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10293",
                                    "value": "0",
                                    "id": "10293",
                                },
                                "customfield_10239": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10300",
                                    "value": "Enterprise",
                                    "id": "10300",
                                },
                                "duedate": None,
                                "statuscategorychangedate": "2020-11-03T18:22:06.790-0500",
                                "customfield_10350": None,
                                "customfield_10351": None,
                                "fixVersions": [],
                                "customfield_10352": None,
                                "customfield_10474": None,
                                "customfield_10353": None,
                                "customfield_10354": None,
                                "customfield_10475": None,
                                "customfield_10476": None,
                                "customfield_10234": None,
                                "customfield_10355": None,
                                "customfield_10356": None,
                                "customfield_10477": None,
                                "customfield_10235": None,
                                "customfield_10346": None,
                                "customfield_10347": None,
                                "customfield_10348": None,
                                "customfield_10349": None,
                                "customfield_10340": None,
                                "customfield_10341": None,
                                "priority": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/priority/3",
                                    "iconUrl": "https://origin-static-assets.s3.amazonaws.com/jira/p3.png",
                                    "name": "Medium",
                                    "id": "3",
                                },
                                "customfield_10343": None,
                                "customfield_10344": None,
                                "customfield_10345": None,
                                "customfield_10335": None,
                                "customfield_10456": None,
                                "customfield_10457": None,
                                "customfield_10336": None,
                                "customfield_10458": None,
                                "customfield_10337": None,
                                "customfield_10338": None,
                                "customfield_10459": None,
                                "customfield_10339": None,
                                "timeestimate": None,
                                "versions": [],
                                "status": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/status/10001",
                                    "description": "",
                                    "iconUrl": "https://datadoghq.atlassian.net/",
                                    "name": "Done",
                                    "id": "10001",
                                    "statusCategory": {
                                        "self": "https://datadoghq.atlassian.net/rest/api/3/statuscategory/3",
                                        "id": 3,
                                        "key": "done",
                                        "colorName": "green",
                                        "name": "Done",
                                    },
                                },
                                "customfield_10450": None,
                                "customfield_10451": None,
                                "customfield_10330": None,
                                "customfield_10331": None,
                                "customfield_10452": None,
                                "customfield_10453": None,
                                "customfield_10332": None,
                                "customfield_10333": None,
                                "customfield_10454": None,
                                "customfield_10334": None,
                                "customfield_10455": None,
                                "customfield_10324": None,
                                "customfield_10688": None,
                                "customfield_10325": None,
                                "customfield_10326": None,
                                "customfield_10448": None,
                                "customfield_10327": None,
                                "aggregatetimeestimate": None,
                                "customfield_10328": None,
                                "customfield_10329": None,
                                "creator": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/user?accountId=557058%3Aa01b4872-0086-4bc3-903e-23f26637afa2",
                                    "accountId": "557058:a01b4872-0086-4bc3-903e-23f26637afa2",
                                    "avatarUrls": {
                                        "48x48": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "24x24": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "16x16": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "32x32": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                    },
                                    "displayName": "Zendesk Support for Jira",
                                    "active": True,
                                    "timeZone": "America/New_York",
                                    "accountType": "app",
                                },
                                "aggregateprogress": {"progress": 0, "total": 0},
                                "customfield_10320": None,
                                "customfield_10321": None,
                                "customfield_10322": None,
                                "customfield_10443": None,
                                "customfield_10323": None,
                                "customfield_10313": None,
                                "customfield_10314": None,
                                "customfield_10315": None,
                                "customfield_10316": None,
                                "customfield_10317": None,
                                "customfield_10318": None,
                                "customfield_10319": None,
                                "timespent": None,
                                "aggregatetimespent": None,
                                "customfield_10310": None,
                                "customfield_10431": None,
                                "customfield_10311": None,
                                "customfield_10312": None,
                                "customfield_10302": None,
                                "customfield_10303": None,
                                "customfield_10304": None,
                                "customfield_10425": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Priority:",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Fill in details below for the issue type (Log Collection, Processing issue, In-app issue). Delete the ones that don't apply.",
                                                    "marks": [{"type": "em"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Log Collection issue - Please provide",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Agent status: If they are using the agent, always add the agent status",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Third party Agent configuration file: if they are using a third party log shipper, ask their configuration file",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Docker inspect: If the issue is linked to a specific container, please provide the result of the docker inspect command for that container.",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Processing issue Please provide:",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Partlow link to the logs: If the issue is about parsing, filtering, or in-app, please add a partlow link to the logs with the issue",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "sample of logs with the issue (copy paste or screenshot of a log as partlow links do not last forever)",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Screenshot of the pipeline/processor",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "expected result",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "In-app issue - Please provide",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Partlow Link to logs with the issue",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Please add details about the network tab of the console output when replicating a front end issue (internal error on search, ...)",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "----------------------------",
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10305": None,
                                "customfield_10427": None,
                                "customfield_10306": None,
                                "customfield_10307": None,
                                "customfield_10429": None,
                                "customfield_10308": None,
                                "customfield_10309": None,
                                "workratio": -1,
                                "created": "2020-10-30T18:33:10.871-0400",
                                "customfield_10300": None,
                                "customfield_10301": None,
                                "customfield_10410": None,
                                "customfield_10411": None,
                                "customfield_10402": None,
                                "security": None,
                                "customfield_10405": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "*"},
                                                {
                                                    "type": "text",
                                                    "text": "NOTE",
                                                    "marks": [{"type": "strong"}],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "*: Strikethrough each one that is true (aside from adding strikethrough, no need to provide any additional information here or edit this content)",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "1. Sensitive data is no longer being received by Datadog.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "2. Precise time range of sensitive logs provided.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "3. User understands the deletion cannot be scoped to a specific, user-provided query & time range (more than the sensitive logs will be deleted).",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "4. User confirms it is OK to delete that the range of logs that the T2/PM communicates must be deleted.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "5. Admin user approval on final range of logs that need to be deleted.",
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10406": None,
                                "customfield_10409": "2020-11-03",
                            },
                        },
                        {
                            "expand": "operations,versionedRepresentations,editmeta,changelog,renderedFields",
                            "id": "152821",
                            "self": "https://datadoghq.atlassian.net/rest/api/3/issue/152821",
                            "key": "AGENT-5269",
                            "fields": {
                                "resolution": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/resolution/10000",
                                    "id": "10000",
                                    "description": "Work has been completed on this issue.",
                                    "name": "Done",
                                },
                                "lastViewed": None,
                                "customfield_10183": None,
                                "customfield_10184": None,
                                "customfield_10185": None,
                                "labels": ["jira_escalated"],
                                "aggregatetimeoriginalestimate": None,
                                "issuelinks": [],
                                "assignee": None,
                                "components": [],
                                "customfield_10290": None,
                                "customfield_10291": None,
                                "customfield_10292": None,
                                "customfield_10293": None,
                                "customfield_10294": None,
                                "customfield_10295": None,
                                "customfield_10296": None,
                                "customfield_10297": None,
                                "customfield_10298": None,
                                "customfield_10299": None,
                                "customfield_10280": None,
                                "subtasks": [],
                                "customfield_10281": None,
                                "customfield_10282": None,
                                "customfield_10283": None,
                                "customfield_10284": None,
                                "customfield_10163": None,
                                "customfield_10164": None,
                                "customfield_10285": None,
                                "reporter": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/user?accountId=5ee158269352c00aa8e75964",
                                    "accountId": "5ee158269352c00aa8e75964",
                                    "emailAddress": "khang.truong@datadoghq.com",
                                    "avatarUrls": {
                                        "48x48": "https://secure.gravatar.com/avatar/2617438827026e7e6458da877547e519?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FKT-3.png",
                                        "24x24": "https://secure.gravatar.com/avatar/2617438827026e7e6458da877547e519?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FKT-3.png",
                                        "16x16": "https://secure.gravatar.com/avatar/2617438827026e7e6458da877547e519?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FKT-3.png",
                                        "32x32": "https://secure.gravatar.com/avatar/2617438827026e7e6458da877547e519?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FKT-3.png",
                                    },
                                    "displayName": "Khang Truong",
                                    "active": True,
                                    "timeZone": "America/New_York",
                                    "accountType": "atlassian",
                                },
                                "customfield_10286": None,
                                "customfield_10165": None,
                                "customfield_10287": None,
                                "customfield_10288": None,
                                "customfield_10289": None,
                                "customfield_10710": None,
                                "customfield_10711": None,
                                "customfield_10712": None,
                                "customfield_10713": None,
                                "customfield_10714": None,
                                "customfield_10715": None,
                                "customfield_10716": None,
                                "progress": {"progress": 0, "total": 0},
                                "votes": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issue/AGENT-5269/votes",
                                    "votes": 0,
                                    "hasVoted": False,
                                },
                                "issuetype": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issuetype/11626",
                                    "id": "11626",
                                    "description": "",
                                    "iconUrl": "https://datadoghq.atlassian.net/secure/viewavatar?size=medium&avatarId=10308&avatarType=issuetype",
                                    "name": "Agent Integrations",
                                    "subtask": False,
                                    "avatarId": 10308,
                                },
                                "customfield_10390": None,
                                "customfield_10270": None,
                                "customfield_10391": None,
                                "customfield_10271": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://support-admin.us1.prod.dog/admin/switch_handle_get/org_id/479442?next_url=%2Fscreen%2Fintegration%2F242%2Fcisco-aci---overview%3Ffrom_ts%3D1604062260518%26live%3Dtrue%26to_ts%3D1604065860518",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://support-admin.us1.prod.dog/admin/switch_handle_get/org_id/479442?next_url=%2Fscreen%2Fintegration%2F242%2Fcisco-aci---overview%3Ffrom_ts%3D1604062260518%26live%3Dtrue%26to_ts%3D1604065860518"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10392": None,
                                "customfield_10272": None,
                                "customfield_10393": None,
                                "project": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/project/10435",
                                    "id": "10435",
                                    "key": "AGENT",
                                    "name": "Support - Agent",
                                    "projectTypeKey": "software",
                                    "simplified": False,
                                    "avatarUrls": {
                                        "48x48": "https://datadoghq.atlassian.net/secure/projectavatar?pid=10435&avatarId=10424",
                                        "24x24": "https://datadoghq.atlassian.net/secure/projectavatar?size=small&s=small&pid=10435&avatarId=10424",
                                        "16x16": "https://datadoghq.atlassian.net/secure/projectavatar?size=xsmall&s=xsmall&pid=10435&avatarId=10424",
                                        "32x32": "https://datadoghq.atlassian.net/secure/projectavatar?size=medium&s=medium&pid=10435&avatarId=10424",
                                    },
                                },
                                "customfield_10394": None,
                                "customfield_10273": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10274": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10275": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10276": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10277": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10278": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "N/A"}
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10279": None,
                                "customfield_10269": None,
                                "customfield_10027": None,
                                "customfield_10149": None,
                                "resolutiondate": "2020-11-10T09:11:51.018-0500",
                                "watches": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/issue/AGENT-5269/watchers",
                                    "watchCount": 5,
                                    "isWatching": False,
                                },
                                "customfield_10380": None,
                                "customfield_10381": None,
                                "customfield_10260": None,
                                "customfield_10382": None,
                                "customfield_10261": None,
                                "customfield_10383": None,
                                "customfield_10020": None,
                                "customfield_10262": "7.23.1",
                                "customfield_10021": None,
                                "customfield_10384": None,
                                "customfield_10263": None,
                                "customfield_10385": None,
                                "customfield_10022": "2020-10-30T13:48:52.395-0400",
                                "customfield_10023": "11887_*:*_2_*:*_1618765_*|*_11886_*:*_2_*:*_362833297",
                                "customfield_10265": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Flare attached",
                                                }
                                            ],
                                        }
                                    ],
                                },
                                "customfield_10386": None,
                                "customfield_10387": None,
                                "customfield_10267": None,
                                "customfield_10388": None,
                                "customfield_10389": None,
                                "customfield_10268": None,
                                "customfield_10379": None,
                                "customfield_10258": None,
                                "customfield_10016": None,
                                "customfield_10259": None,
                                "customfield_10017": None,
                                "customfield_10018": {
                                    "hasEpicLinkFieldDependency": False,
                                    "showField": False,
                                    "nonEditableReason": {
                                        "reason": "PLUGIN_LICENSE_ERROR",
                                        "message": "The Parent Link is only available to Jira Premium users.",
                                    },
                                },
                                "customfield_10019": "2|i001uv:",
                                "updated": "2020-11-10T09:11:54.352-0500",
                                "customfield_10490": None,
                                "timeoriginalestimate": None,
                                "customfield_10370": None,
                                "customfield_10491": None,
                                "customfield_10371": None,
                                "customfield_10250": None,
                                "customfield_10492": None,
                                "description": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Customer is missing cisco tenant metrics cisco_aci.tenant.* , only some cisco_Aci metrics are collected.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "Partlow : "},
                                                {
                                                    "type": "text",
                                                    "text": "https://support-admin.us1.prod.dog/admin/switch_handle_get/org_id/479442?next_url=%2Fmetric%2Fsummary%3Ffilter%3Dcisco_aci",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://support-admin.us1.prod.dog/admin/switch_handle_get/org_id/479442?next_url=%2Fmetric%2Fsummary%3Ffilter%3Dcisco_aci"
                                                            },
                                                        }
                                                    ],
                                                },
                                                {"type": "text", "text": " "},
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Investigation:",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "Cisco check is OK : ",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/z8uYB7mE",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/z8uYB7mE"
                                                            },
                                                        }
                                                    ],
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/geuqBlOw",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/geuqBlOw"
                                                            },
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "yaml file seems to be properly configured :",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/OAuJNzok",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/OAuJNzok"
                                                            },
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Asked on #support-agent-intg for help :",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "https://a.cl.ly/12urb6oQ",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://a.cl.ly/12urb6oQ"
                                                            },
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "heading",
                                            "attrs": {"level": 3},
                                            "content": [
                                                {"type": "text", "text": "Attachments"}
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Screen Shot 2020-10-20 at 1.01.15 PM.png",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/kQTrp3a58S91EE09dgvYy69xo/?name=Screen+Shot+2020-10-20+at+1.01.15+PM.png"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Screen Shot 2020-10-20 at 12.58.47 PM.png",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/uBa5UbBwivTdmxW4tt1Av3e2H/?name=Screen+Shot+2020-10-20+at+12.58.47+PM.png"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "datadog-agent-2020-10-28-15-31-36.zip",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://datadog.zendesk.com/attachments/token/TEW1uwhEa4sAsJghQcCZozVVt/?name=datadog-agent-2020-10-28-15-31-36.zip"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Please see Zendesk Support tab for further comments and attachments.",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10251": None,
                                "customfield_10372": None,
                                "customfield_10373": None,
                                "customfield_10010": None,
                                "customfield_10252": None,
                                "customfield_10253": None,
                                "customfield_10374": None,
                                "customfield_10375": None,
                                "customfield_10254": None,
                                "customfield_10133": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Postmortem processes can be found here:  ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "https://docs.google.com/document/d/1Jon66NB-QsOqAI9E2T9OgjlZIKwN_zuKPL9oOV4Xf_8/edit",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://docs.google.com/document/d/1Jon66NB-QsOqAI9E2T9OgjlZIKwN_zuKPL9oOV4Xf_8/edit"
                                                            },
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "1. Remember to set a due date 5 working days forward on the card",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "2. Remember to add the appropriate Engineering Director and VP to the card",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "3. Add the internal and public postmortems as attachments",
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "4. Drop them in the Engineering shared drive (under postmortems)",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Please add the following information here: ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Organization(s) Requesting",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Date and Time of Outage",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Link to Slack Channel and Link to Incident App",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Zendesk ticket(s) ",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "—Additional Notes/Requests",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "The original Trello URL is ",
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "https://trello.com/c/hBSVjH3Y/115-template-card",
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": "https://trello.com/c/hBSVjH3Y/115-template-card"
                                                            },
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10376": None,
                                "customfield_10255": None,
                                "customfield_10256": None,
                                "customfield_10014": None,
                                "customfield_10377": None,
                                "customfield_10015": None,
                                "customfield_10378": None,
                                "customfield_10257": None,
                                "customfield_10247": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10387",
                                    "value": "Cisco ACI",
                                    "id": "10387",
                                },
                                "customfield_10368": None,
                                "customfield_10005": None,
                                "customfield_10006": None,
                                "customfield_10369": None,
                                "customfield_10248": None,
                                "customfield_10007": None,
                                "customfield_10249": None,
                                "customfield_10008": None,
                                "customfield_10009": None,
                                "summary": "Cisco_aci.tenant.* metric missing",
                                "customfield_10480": None,
                                "customfield_10481": None,
                                "customfield_10360": None,
                                "customfield_10361": None,
                                "customfield_10240": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10304",
                                    "value": "No",
                                    "id": "10304",
                                },
                                "customfield_10482": None,
                                "customfield_10483": None,
                                "customfield_10241": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10325",
                                    "value": "Missing Data",
                                    "id": "10325",
                                },
                                "customfield_10362": None,
                                "customfield_10000": "{}",
                                "customfield_10363": None,
                                "customfield_10242": "N/A",
                                "customfield_10001": None,
                                "customfield_10364": None,
                                "customfield_10243": None,
                                "customfield_10002": None,
                                "customfield_10365": None,
                                "customfield_10244": None,
                                "customfield_10003": None,
                                "customfield_10245": None,
                                "customfield_10246": None,
                                "customfield_10367": None,
                                "customfield_10004": None,
                                "customfield_10478": None,
                                "customfield_10236": "479442",
                                "customfield_10357": None,
                                "customfield_10237": "Tivity Health Services, LLC",
                                "customfield_10358": None,
                                "customfield_10479": None,
                                "environment": None,
                                "customfield_10359": None,
                                "customfield_10238": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10295",
                                    "value": "2",
                                    "id": "10295",
                                },
                                "customfield_10239": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/customFieldOption/10299",
                                    "value": "Pro",
                                    "id": "10299",
                                },
                                "duedate": None,
                                "statuscategorychangedate": "2020-11-10T09:11:51.567-0500",
                                "customfield_10350": None,
                                "customfield_10351": None,
                                "customfield_10352": None,
                                "fixVersions": [],
                                "customfield_10474": None,
                                "customfield_10353": None,
                                "customfield_10475": None,
                                "customfield_10354": None,
                                "customfield_10234": None,
                                "customfield_10355": None,
                                "customfield_10476": None,
                                "customfield_10477": None,
                                "customfield_10235": None,
                                "customfield_10356": None,
                                "customfield_10346": None,
                                "customfield_10347": None,
                                "customfield_10348": None,
                                "customfield_10349": None,
                                "customfield_10340": None,
                                "customfield_10341": None,
                                "priority": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/priority/3",
                                    "iconUrl": "https://origin-static-assets.s3.amazonaws.com/jira/p3.png",
                                    "name": "Medium",
                                    "id": "3",
                                },
                                "customfield_10343": None,
                                "customfield_10344": None,
                                "customfield_10345": None,
                                "customfield_10456": None,
                                "customfield_10335": None,
                                "customfield_10336": None,
                                "customfield_10457": None,
                                "customfield_10458": None,
                                "customfield_10337": None,
                                "customfield_10459": None,
                                "customfield_10338": None,
                                "customfield_10339": None,
                                "timeestimate": None,
                                "versions": [],
                                "status": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/status/10001",
                                    "description": "",
                                    "iconUrl": "https://datadoghq.atlassian.net/",
                                    "name": "Done",
                                    "id": "10001",
                                    "statusCategory": {
                                        "self": "https://datadoghq.atlassian.net/rest/api/3/statuscategory/3",
                                        "id": 3,
                                        "key": "done",
                                        "colorName": "green",
                                        "name": "Done",
                                    },
                                },
                                "customfield_10450": None,
                                "customfield_10330": None,
                                "customfield_10451": None,
                                "customfield_10452": None,
                                "customfield_10331": None,
                                "customfield_10332": None,
                                "customfield_10453": None,
                                "customfield_10333": None,
                                "customfield_10454": None,
                                "customfield_10334": None,
                                "customfield_10455": None,
                                "customfield_10324": None,
                                "customfield_10325": None,
                                "customfield_10688": None,
                                "customfield_10326": None,
                                "customfield_10327": None,
                                "customfield_10448": None,
                                "aggregatetimeestimate": None,
                                "customfield_10328": None,
                                "customfield_10329": None,
                                "creator": {
                                    "self": "https://datadoghq.atlassian.net/rest/api/3/user?accountId=557058%3Aa01b4872-0086-4bc3-903e-23f26637afa2",
                                    "accountId": "557058:a01b4872-0086-4bc3-903e-23f26637afa2",
                                    "avatarUrls": {
                                        "48x48": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "24x24": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "16x16": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                        "32x32": "https://secure.gravatar.com/avatar/bc07317d8cbdde0ff466674bb68a9dd7?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FZJ-1.png",
                                    },
                                    "displayName": "Zendesk Support for Jira",
                                    "active": True,
                                    "timeZone": "America/New_York",
                                    "accountType": "app",
                                },
                                "aggregateprogress": {"progress": 0, "total": 0},
                                "customfield_10320": None,
                                "customfield_10321": None,
                                "customfield_10322": None,
                                "customfield_10443": None,
                                "customfield_10323": None,
                                "customfield_10313": None,
                                "customfield_10314": None,
                                "customfield_10315": None,
                                "customfield_10316": None,
                                "customfield_10317": None,
                                "customfield_10318": None,
                                "customfield_10319": None,
                                "timespent": None,
                                "aggregatetimespent": None,
                                "customfield_10431": None,
                                "customfield_10310": None,
                                "customfield_10311": None,
                                "customfield_10312": None,
                                "customfield_10302": None,
                                "customfield_10303": None,
                                "customfield_10304": None,
                                "customfield_10425": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Priority:",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Fill in details below for the issue type (Log Collection, Processing issue, In-app issue). Delete the ones that don't apply.",
                                                    "marks": [{"type": "em"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Log Collection issue - Please provide",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Agent status: If they are using the agent, always add the agent status",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Third party Agent configuration file: if they are using a third party log shipper, ask their configuration file",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Docker inspect: If the issue is linked to a specific container, please provide the result of the docker inspect command for that container.",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Processing issue Please provide:",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Partlow link to the logs: If the issue is about parsing, filtering, or in-app, please add a partlow link to the logs with the issue",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "sample of logs with the issue (copy paste or screenshot of a log as partlow links do not last forever)",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Screenshot of the pipeline/processor",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "expected result",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "In-app issue - Please provide",
                                                    "marks": [{"type": "strong"}],
                                                }
                                            ],
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Partlow Link to logs with the issue",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "Please add details about the network tab of the console output when replicating a front end issue (internal error on search, ...)",
                                                                },
                                                                {"type": "hardBreak"},
                                                                {
                                                                    "type": "text",
                                                                    "text": "Description of the problem: Please add screenshots and GIF if appropriate. It always helps",
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User is doing this",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User click there",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User sees this data and perform this action",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "User got this unexpected behaviour",
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "----------------------------",
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10305": None,
                                "customfield_10427": None,
                                "customfield_10306": None,
                                "customfield_10307": None,
                                "customfield_10429": None,
                                "customfield_10308": None,
                                "customfield_10309": None,
                                "workratio": -1,
                                "created": "2020-10-30T09:55:06.645-0400",
                                "customfield_10300": None,
                                "customfield_10301": None,
                                "customfield_10410": None,
                                "customfield_10411": None,
                                "customfield_10402": None,
                                "security": None,
                                "customfield_10405": {
                                    "version": 1,
                                    "type": "doc",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "*"},
                                                {
                                                    "type": "text",
                                                    "text": "NOTE",
                                                    "marks": [{"type": "strong"}],
                                                },
                                                {
                                                    "type": "text",
                                                    "text": "*: Strikethrough each one that is true (aside from adding strikethrough, no need to provide any additional information here or edit this content)",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "1. Sensitive data is no longer being received by Datadog.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "2. Precise time range of sensitive logs provided.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "3. User understands the deletion cannot be scoped to a specific, user-provided query & time range (more than the sensitive logs will be deleted).",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "4. User confirms it is OK to delete that the range of logs that the T2/PM communicates must be deleted.",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "5. Admin user approval on final range of logs that need to be deleted.",
                                                }
                                            ],
                                        },
                                    ],
                                },
                                "customfield_10406": None,
                                "customfield_10409": "2020-11-10",
                            },
                        },
                    ],
                }
                self.status_code = "<Response [200]>"

            def __str__(self):
                return "<Response [200]>"

            def json(self):
                return self.json_data

        if args[0] != None:
            return MockResponse()
        return MockResponse()

    @mock.patch("requests.request", side_effect=mocked_api_response)
    def test_jira_query(self, mock_api):

        # a, test_issues_dict = jira_query(
        #     self.board_name,
        #     self.jqlquery,
        #     self.nb_days_before,
        #     self.start_date,
        #     self.name,
        # )

        api_response = jira_query(
            self.board_name, self.target_column, self.search_date, self.auth
        )

        a, test_issues_dict = unpack_api_response(
            self.board_name,
            self.nb_days_before,
            self.window_end_date,
            api_response,
            self.auth,
        )

        # "correct" values
        cissues_dict = {
            "153075": {
                "issue_id": "153075",
                "issue_reporter": "rachel.rath@datadoghq.com",
                "issue_created": datetime.datetime(
                    2020,
                    10,
                    30,
                    18,
                    33,
                    10,
                    871000,
                    tzinfo=datetime.timezone(
                        datetime.timedelta(days=-1, seconds=72000)
                    ),
                ),
                "issue_key": "AGENT-5272",
                "reached_eng": 0,
                "lifetime": 31,
                "issuetype": "Agent Core",
                "issue_service": "Linux",
                "issue_issue": "Logging",
            },
            "152821": {
                "issue_id": "152821",
                "issue_reporter": "khang.truong@datadoghq.com",
                "issue_created": datetime.datetime(
                    2020,
                    10,
                    30,
                    9,
                    55,
                    6,
                    645000,
                    tzinfo=datetime.timezone(
                        datetime.timedelta(days=-1, seconds=72000)
                    ),
                ),
                "issue_key": "AGENT-5269",
                "reached_eng": 0,
                "lifetime": 31,
                "issuetype": "Agent Integrations",
                "issue_service": "Cisco ACI",
                "issue_issue": "Missing Data",
            },
        }

        self.assertEqual(cissues_dict, test_issues_dict)


def main():
    unittest.main()


if __name__ == "__main__":
    main()
