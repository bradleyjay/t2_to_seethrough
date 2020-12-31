import requests

import json
import os
from requests.auth import HTTPBasicAuth

# from datetime import date

# import datetime
# import sys

headers = {"Accept": "application/json"}

url = (
    "https://datadoghq.atlassian.net/rest/api/2/issue/86611/comment"
    # + "&maxResults=0"
)

# url = (
#     "https://datadoghq.atlassian.net/rest/api/2/issue/METS-604/comment
#     # + "&maxResults=0"
# )

auth = HTTPBasicAuth(os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_KEY"))
response = requests.request("GET", url, headers=headers, auth=auth)

f = open("comments.dat", "a+")
f.write(json.dumps(response.json(), indent=4, separators=(",", ": ")))
f.close()
