    
#predefine parameters
# colList = ['Region', 'Nationality', 'area_of_study', 'EnrolmentPeriod']\
#             + ['Age', 'Recency', 'OfferMonth', 'CountryOfResidence', 'OfferYear', 'CourseType', 'IsRisk1', 'StudentType']

#colList needed from raw table i.e keys of _samples.json
colListNeeded = ['Age', 'LoS', 'FirstStudentStatus', 'Faculty', 'FeeStatus', 'CORRegion', 'InitialOfferStatus', 'ProspectType', 'EnrolledNumeric', 'EmailDomainGroup', 'CourseGroup']

#REST endpoint
url = 'http://b606586a-98ee-44a3-b90a-17bfda19a92e.australiaeast.azurecontainer.io/score'

# #load encoder, trained model
# encoderFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_Encoder12Features.sav'
# modelFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_RF_12Features.sav'
# #file to update area_of_study
# updateFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/UTS College Updated Course Info.xlsx"
# #file for tag history
# tagFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/2021-07-28_StudentTagHistory_Insearch.csv"

# threshold = 0.3
