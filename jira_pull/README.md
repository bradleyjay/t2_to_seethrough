This script pulls JIRA stats from each team's Jira board. Each board's stats end up in their own CSV, and all data is added to allBoardsReport.csv. 

Note: each process is backrounded, and runs in parallel. The current window will periodically show % complete for each, and will note when complete.

Files:

- `launch_api_calls.sh`: runscript
- `jira_stats_api_call.py`: Python API query script
- `board_list.dat`: list of Jira projects to query
- `creds.dat`: API token and user email credentials.
- `combine_reports.sh`: final data generation script
- `allBoardsReport.csv`: final data

To run:
0. Set start date in jira_stats_api_call.py.
1. `chmod +x launch_api_calls.sh combine_reports.sh`
2. `./launch_api_calls.sh`

When each has finished, run:

3. `./combine_reports.sh`

## Usage

- Set *start_days_ago* for your purpose:
  - start_days_ago = 90 for changelog and tag breakdown reports
  - start_days_ago = 120 for returning escalation count data

Today, these use two different windows, but there's one query made. For now, toggling is required.

## Running Tests

jira_pull
├── jira_stats_api_call.py
└── tests
      └── test_jira_pull.py

To run our tests, use:

`python3 -m unittest tests.test_jira_pull`

## Open Issues:

- TTFT isn't quite right. Choosing to file issues under the day they were touched vs. the day they were created skews reporting quite a bit. Investigate, determine if filing under creation date checks out.
- Refactor into helper functions
- Improve how we determine if an issue actually reached Eng (today, we just check if the Issue reached Eng Triage / In Progress)
- Route data to Datadog, automate running of script
- Pull data for other teams