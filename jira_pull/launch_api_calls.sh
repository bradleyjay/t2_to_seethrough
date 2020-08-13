#!/bin/bash

source creds.dat
while IFS= read -r line; do
# echo $line

  # for i in `seq 1 3`;
    # do
  python3 jira_stats_api_call.py $line &
    # done

done < board_list.dat