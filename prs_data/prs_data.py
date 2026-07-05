import sys
print(sys.path)
from pathlib import Path
import csv
import pandas as pd

path = Path('/home/mypiwh/apache/prs_data/131337_202603E.csv')
lines = path.read_text(encoding='utf-8') .splitlines()

reader = csv.DictReader(lines)
header_row = next(reader)

#Extract song code
prsdata_list = []
for row in (reader):
    prsdata_list.append(row)
    
#print (prsdata_list)


# Read the CSV file into a DataFrame
df = pd.read_csv('/home/mypiwh/apache/prs_data/131337_202603E.csv')

print(df[["Song Code", "Song Title", "Source Name", "Income Type Name", "Main Income Type Name", "Royalty Payable"]])