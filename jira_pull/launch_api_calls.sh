#!/bin/bash

source creds.dat
rm orphans.dat || echo 'No Orphans.dat file to remove.'

# uncomment to test single call
# python3 jira_stats_api_call.py METS
# python3 jira_stats_api_call.py AGENT 

# # comment out the following to test
while IFS= read -r line; do

  rm ${line}-*.csv || echo 'No $line csv data files to remove.'
  
  python3 jira_stats_api_call.py $line &

done < board_list.dat