#!/bin/bash

# clean old reports
rm allBoardsCOUNT.csv allBoardsTTFT.csv # allBoardsReport.csv 

# gather data by type
cat *-count*.csv >> allBoardsCOUNT.csv
cat *-ttft*.csv >> allBoardsTTFT.csv

# combine to one report
# cat allBoards*.csv >> allBoardsReport.csv