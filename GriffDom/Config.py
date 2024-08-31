    
#predefine parameters
# colList = ['Region', 'Nationality', 'area_of_study', 'EnrolmentPeriod']\
#             + ['Age', 'Recency', 'OfferMonth', 'CountryOfResidence', 'OfferYear', 'CourseType', 'IsRisk1', 'StudentType']

#colList needed from raw table i.e keys of _samples.json
colListNeeded = ['CourseGroup', 'EmailDomain', 'Intake', 'OfferMonth', 'ProgramEncoded']

#REST endpoint
# url = 'http://35d6205d-63ad-4481-bbb5-d81c5461763e.australiaeast.azurecontainer.io/score'

#trained model and encoder
OneHotEncoderFilename = "Model/2024-05-28_Encoder_5Features.sav"
TargetEncoderFilename = "Model/2024-05-28_TargetEncoder.sav"
ModelFilename = 'Model/2024-05-28_XGB_5Features.sav'

# #load encoder, trained model
# encoderFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_Encoder12Features.sav'
# modelFilename = 'C:/Users/JiunShyanGoh/Documents/MachineLearning/Model/UTS/2021-08-06_UTS_RF_12Features.sav'
# #file to update area_of_study
# updateFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/UTS College Updated Course Info.xlsx"
# #file for tag history
# tagFilename = "C:/Users/JiunShyanGoh/Documents/EDA/Data/Raw/UTS/2021-07-28_StudentTagHistory_Insearch.csv"

threshold = 0.5

#high, med and low label
highLabel = "PT_ENP_TagAXXXX_HIGHXXXX"
mediumLabel = "PT_ENP_TagAXXXX_MEDXXXXX"
lowLabel = "PT_ENP_TagAXXXX_LOWXXXXX"
