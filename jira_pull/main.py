import querycore2
import os, sys
import json

boardname = "METS"
jql = "Project = METS AND created >= startOfDay(-20) AND created <= endOfDay(-5)"

auth_email = os.environ.get("JIRA_EMAIL")
auth_token = os.environ.get("JIRA_API_KEY")

jc = querycore2.JiraClient(auth_email, auth_token)
issues = jc.fetch_jql(jql)
print(len(issues))

escalation_count = len(issues)
type_dict = {}

for issue in issues:
    typedict[issue["issue_type"]]
    