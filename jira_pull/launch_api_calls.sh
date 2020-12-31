#!/bin/bash

source creds.dat

echo 'JIRA PULL - grab Issue data and stats from Jira for individual boards, or all at once.'
echo $'\nboardnames:'

cat board_list.dat

echo $'\nCleaning up...'
rm orphans.dat || echo $'No Orphans.dat file to remove.\n'

read -p "Runmode? (enter boardname, or ALL): " runmode

if [[ $runmode == '' ]]; then
    echo "Unknown entry '$runmode'."
elif  grep -qF "$runmode" ./board_list.dat; then
    # test a single board, IF present in board_list.dat
    echo "Pulling JIRA stats for $runmode."
    python3 jira_stats_api_call.py $runmode 
elif  [[ $runmode == "ALL" ]]; then
    # Pull data for all boards in board_list.dat
    while IFS= read -r line; do
      rm ${line}-*.csv || echo "No $line csv data files to remove."
      python3 jira_stats_api_call.py $line &
    done < board_list.dat
else
    # unknown input, abort
    echo "Unknown entry '$runmode'" 
fi

# uncomment to test single call
# python3 jira_stats_api_call.py METS
# python3 jira_stats_api_call.py AGENT 

# # comment out the following to test
