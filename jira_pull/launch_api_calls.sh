#!/bin/bash

source creds.dat
rm orphans.dat || echo 'No Orphans.dat file to remove.'

# python3 jira_stats_api_call.py METS
while IFS= read -r line; do

  rm ${line}-*.csv || echo 'No $line csv data files to remove.'
  
  python3 jira_stats_api_call.py $line &

done < board_list.dat