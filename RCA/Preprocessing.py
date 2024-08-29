from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from RCA.Config import *
import urllib.request
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans
from datetime import datetime

class RCA_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
        df['InitialOfferDate'] = pd.to_datetime(df['InitialOfferDate'], format='%d/%m/%Y')
        df['CensusDate'] = pd.to_datetime(df['CensusDate'], format='%d/%m/%Y')
        
        # Calculate the difference in days between CensusDate and InitialOfferDate
        df['Recency_time'] = (df['CensusDate'] - df['InitialOfferDate']).dt.days
        
        # If you want to ensure Recency_time is numeric
        df['Recency_time'] = df['Recency_time'].astype(float)

        # semester
        df['Semester'] = df['EnrPeriod'].str[:10]
        
        # Create the 'Recency' column based on the conditions provided
        conditions = [
            (df['Recency_time'] >= 270),
            (df['Recency_time'] >= 152) & (df['Recency_time'] < 270),
            (df['Recency_time'] > 0) & (df['Recency_time'] < 152)
        ]
        
        choices = ['PAST', 'RECENT', 'MOST RECENT']
        
        df['Recency'] = np.select(conditions, choices, default='NEGATIVE')

        #Processing
        df['Enrolled'] = 1
        #paste from _sample.json[0].keys()
        sample_records = df[[i for i in colListNeeded]].to_dict('records')
        return sample_records

    #consume REST endpoint from Azure AI
    def callWebService(self, url, body, headers):
        req = urllib.request.Request(url, body, headers) 

        try:
            response = urllib.request.urlopen(req)

            # If you are using Python 3+, replace urllib2 with urllib.request in the above code:
            # req = urllib.request.Request(url, body, headers) 
            # response = urllib.request.urlopen(req)

            result = response.read()
            return result
        #     print(result) 
        except  urllib.error.HTTPError as error:
            print("The request failed with status code: " + str(error.code))
            # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
            print(error.info())
            print(json.loads(error.read()))  

    def finalProcessing(self, body):

        headers = {'Content-Type':'application/json'}
        body = str.encode(json.dumps(body))
        result = self.callWebService(url = url, body = body, headers = headers)
        resultJson = json.loads(json.loads(result))
        dfResult = pd.DataFrame(resultJson['result'], columns = colListNeeded + ['Scored Labels', 'Scored Probabilities'])
        #Data Manipulation to get final output
        #predefine parameters
        threshold = 0.2
        highTag = "PT_ENP_TagAXXXX_HIGHXXXX"
        mediumTag = "PT_ENP_TagAXXXX_MEDXXXXX"
        lowTag = "PT_ENP_TagAXXXX_LOWXXXXX"
        #version 1
        tagDate = "01/06/2023"
        #version 1.1
        tagDate = "13/06/2024"
        taskType = 'Made Offer'
        df = self.df.copy()

        # Assuming 'df' is your dataframe equivalent to 't1' in SQL
        def assign_general_tag(scored_probabilities):
            if scored_probabilities < 0.09:
                return 'PT_ENP_TagAXXXX_LOWXXXXX'
            elif scored_probabilities < 0.12:
                return 'PT_ENP_TagAXXXX_MEDXXXXX'
            else:
                return 'PT_ENP_TagAXXXX_HIGHXXXX'

        # Apply the function to the 'Scored Probabilities' column
        df['General_Tag'] = dfResult['Scored Probabilities'].apply(assign_general_tag)

        df['Scored Probabilities'] = dfResult['Scored Probabilities']

        result_df = df.copy()

        # Replace NA values in 'COR' column with an empty string
        result_df['COR'] = result_df['COR'].fillna('')

        # Change 'Postgraduate' to 'PG' and 'Undergraduate' to 'UG' in the 'LoS' column
        result_df['LoS'] = result_df['LoS'].str.replace('Postgraduate', 'PG')
        result_df['LoS'] = result_df['LoS'].str.replace('Undergraduate', 'UG')

        # Assign 'Assigned To' based on 'Scored Probabilities'
        result_df['Assigned To'] = np.where(result_df['Scored Probabilities'] < 0.09, 'LOW', 
                                            np.where(result_df['Scored Probabilities'] > 0.12, 'HIGH', 'MED'))

        # Ensure the 'Year' column is a string
        result_df['Year'] = result_df['Year'].astype(str)

        # Create 'Task_Description' column
        result_df['Task_Description'] = (
            result_df['IntakeStatus'] + '-' + 
            result_df['Year'].str[-2:] + '_' + 
            #result_df['Zone'] + '_' + 
            result_df['InitialOfferStatus'].str.replace('Made Offer', 'MO') + ' ' + 
            result_df['COR'] + ' ' + 
            result_df['LoS']
        )

        result_df['TaskCreate'] = result_df['COR'].map(lambda x: 'Yes' if x == 'China' else 'No')
        result_df['Task_Description'] = result_df.apply(lambda x:x['Task_Description'] if x['COR'] == 'China' else '', axis = 1)

        # Add 'tag_date' and 'TaskType' columns
        result_df['tag_date'] = '09/06/2022'
        result_df['TaskType'] = 'Made Offer'

        # Assuming 'result_df' is your DataFrame equivalent to 't1' in SQL
        def assign_task_create(row):
            if row['Tagvalue'] == 'MO_Call_Excluded':
                return 'No'
            elif row['COR'] != 'China':
                return 'No'
            else:
                return 'Yes'

        # Apply the function to each row to create the 'TaskCreate' column
        result_df['TaskCreate'] = result_df.apply(assign_task_create, axis=1)

        # Create 'Scored Labels' based on 'Scored Probabilities'
        result_df['Scored Labels'] = np.where(result_df['Scored Probabilities'] < 0.09, 0, 1)

        finalColumnList = ["AA ClientName", "AA client_id", "AB crms_number","AC_MOTask", "AE_MLTag", 
               "Age", "AgentDirect", "AreaOfStudy", "Campus", "ClientType", "COR", 
               "CORRegion", "CORSubRegion", "CourseName", "Dead", "EmailDomain", 
               "EnrolledNumeric", "EnrPeriod", "Faculty", "FeeStatus", "FirstAgentTag", 
               "FirstStudentStatus", "Gender", "InclusionStatus", "InitialOfferStatus", "IntakeStatus",
               "LoS", "Nationality", "NatRegion", "NatSubRegion", "OfferTagSeq",
               "ProspectType", "Tagvalue", "Year", "Number of Records",
               "InitialOfferDate","CensusDate"] 

        finalColumnList = finalColumnList + ['Scored Labels', 'Scored Probabilities', 'tag_date', 'TaskType','TaskCreate', 'General_Tag', 'Assigned To', 'Task_Description']
        dfFinal = result_df[finalColumnList].copy()
        return dfFinal
