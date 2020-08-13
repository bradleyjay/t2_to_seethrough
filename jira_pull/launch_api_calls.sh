#!/bin/bash

source creds.dat
python3 jira_stats_api_call.py METS

# while IFS= read -r line; do
# # echo $line

#   # for i in `seq 1 3`;
#     # do
#   # python3 jira_stats_api_call.py $line &
#   # python3 jira_stats_api_call.py METS # debug mode - just METS, foreground
#     # done

# done < board_list.dat