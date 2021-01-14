import collections
import json

import requests


class JiraClient:
    URL_BASE = "https://datadoghq.atlassian.net/rest/api/3/{}"

    def __init__(self, auth_email, auth_token):
        session = requests.Session()
        session.auth = requests.auth.HTTPBasicAuth(auth_email, auth_token)
        session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        self.session = session

    def get(self, url, params=None):
        res = self.session.get(
            JiraClient.URL_BASE.format(url),
            params=params,
        )
        res.raise_for_status()
        return res.json()

    def fetch_jql_page(self, jql, start_at=0, max_results=100):
        return self.get(
            "search", params=dict(jql=jql, startAt=start_at, maxResults=max_results)
        )

    def fetch_jql(self, jql):
        issues = []
        start_at = 0
        max_results = 100
        total = 100  # We don't know the total yet, but just start with something to get the while loop going
        while start_at < total:
            result = self.fetch_jql_page(jql, start_at, max_results)
            max_results = result["maxResults"]
            start_at += len(result["issues"])
            total = result["total"]

            issues += result["issues"]
        return issues

    def fetch_issue(self, issue_key):
        return self.get(f"issue/{issue_key}")

    def fetch_issue_changelog(self, issue_key):
        return self.get(
            f"issue/{issue_key}/changelog",
            params=dict(maxResults=500),
        )

    def fetch_issue_comments(self, issue_key):
        return self.get(
            f"issue/{issue_key}/comment",
            params=dict(maxResults=500),
        )


