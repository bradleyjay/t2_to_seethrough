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