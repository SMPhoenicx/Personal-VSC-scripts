'''
This program uses the google sheet and google drive API's to read the House Scoring data,
in order for this program to function succesfully the OFFICIAL HOUSE POINTS google sheet must be shared with the 
following user: sac-official-service@housepointstracker-433517.iam.gserviceaccount.com
'''

import gspread
from google.oauth2 import service_account

'''
I have created a service account to be used by the app to access the sac house tracking spreadsheet
currently authorizing the service account to use google sheets 
'''

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_file("/Users/sumsm/Documents/vsc/Regatta/creds.json", scopes=scope)

client = gspread.authorize(creds)

#OFFICIAL NAME OF THE GOOGLE DOCUMENT GOES HERE (remember must be shared to the client email)
sheet_name = "House Points 24-25"
sheet = client.open(sheet_name).sheet1

#the row number as it appears in google sheets (one-indexed) of the row that contains the house names and house points respectively
name_row = 2
points_row = 1
#row on which actual house name/house points entries begin (NOT JUST THE TITLES) this is NOT the row as it appears in google sheets (zerp-indexed)
entry_col = 1
#row on whcih house/name point entries end (zero-indexed)
end_col = 6

house_names = sheet.row_values(name_row)
house_points = sheet.row_values(points_row)

#create a dictionary where the key is the name of the house and the value is the number of house points
points_dictionary = dict()
for index in range(entry_col, end_col+1):
    points_dictionary[house_names[index]] = house_points[index]
print(points_dictionary)

#create dictionary of most recent event, event["event_name"] gives the name of that event the rest is organzied as the hosue name as key and the points they got from it as value
#TO-DO LATER!!!!