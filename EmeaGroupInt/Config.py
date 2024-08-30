    
#predefine parameters
# colList = ['Region', 'Nationality', 'area_of_study', 'EnrolmentPeriod']\
#             + ['Age', 'Recency', 'OfferMonth', 'CountryOfResidence', 'OfferYear', 'CourseType', 'IsRisk1', 'StudentType']

#colList needed from raw table i.e keys of _samples.json
colListNeeded = ['EnrolledNumeric', 'ClientType', 'ProspectType', 'Age', 'Faculty', 'CORSubRegion', 'CORRegion', 'FeeStatus', 'CourseGroup', 'InitialOfferMonth', 'IsInitialOfferWeekDay', 'Semester']

#REST endpoint
url = 'http://98d001b4-ba74-449a-9a45-d51b69802cb4.australiaeast.azurecontainer.io/score'

#date file
# filename_Date = "External/Date Data.csv"
# filename_Task_Assignment = "External/Task_Assignment_Mapping_2.csv"

# #load encoder, trained model
# encoderFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_Encoder12Features.sav'
# modelFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_RF_12Features.sav'
# #file to update area_of_study
# updateFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/UTS College Updated Course Info.xlsx"
# #file for tag history
# tagFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/2021-07-28_StudentTagHistory_Insearch.csv"

# threshold = 0.3
