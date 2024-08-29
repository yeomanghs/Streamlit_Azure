from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from MacqDom.Config import *
import urllib.request
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans
from datetime import datetime

class MacqDom_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
        df['InitialOfferDate'] = pd.to_datetime(df['InitialOfferDate'], format='%d/%m/%Y')
        df['InitialOfferMonth'] = df['InitialOfferDate'].dt.month
        df['CensusDate'] = pd.to_datetime(df['Census Date'], format='%d/%m/%Y')
        df['Recency_time'] = (df['CensusDate'] - df['InitialOfferDate']).dt.days

        # Ensure 'Recency_time' is numeric if needed
        df['Recency_time'] = df['Recency_time'].astype(float)

        # Recency_time
        # Create the 'Recency' column based on the conditions provided
        conditions = [
            (df['Recency_time'] >= 130),
            (df['Recency_time'] >= 88) & (df['Recency_time'] < 130),
            (df['Recency_time'] > 0) & (df['Recency_time'] < 88)
        ]
        
        choices = ['PAST', 'RECENT', 'MOST RECENT']
        df['Recency'] = np.select(conditions, choices, default='NEGATIVE')

        # Create StudentType based on CountryOfResidence
        df['StudentType'] = df['CountryOfResidence'].apply(lambda x: 'Domestic' if x == 'Australia' else 'International')

        #Processing
        df['EnrolledNumeric'] = 1
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
            if scored_probabilities < 0.22:
                return lowTag
            elif scored_probabilities < 0.44:
                return mediumTag
            else:
                return highTag

        # Apply the function to the 'Scored Probabilities' column
        df['General_Tag'] = dfResult['Scored Probabilities'].apply(assign_general_tag)

        df['Scored Probabilities'] = dfResult['Scored Probabilities']

        result_df = df.copy()

        result_df['Task_Description2'] = np.where(
            result_df['Scored Probabilities'] < 0.22,
            'LOW_' + result_df['EnrolmentPeriod'].astype(str) + '_' + 
                    result_df['IntakeYear'].astype(str) + '_' + 
                    result_df['InitialOffer'].astype(str) + '_' + 
                    result_df['CountryOfResidence'].astype(str),
            np.where(
                result_df['Scored Probabilities'] < 0.44,
                'MED_' + result_df['EnrolmentPeriod'].astype(str) + '_' + 
                        result_df['IntakeYear'].astype(str) + '_' + 
                        result_df['InitialOffer'].astype(str) + '_' + 
                        result_df['CountryOfResidence'].astype(str),
                'HIGH_' + result_df['EnrolmentPeriod'].astype(str) + '_' + 
                        result_df['IntakeYear'].astype(str) + '_' + 
                        result_df['InitialOffer'].astype(str) + '_' + 
                        result_df['CountryOfResidence'].astype(str)
            )
        )

        # Replace NA values in 'COR' column with an empty string
        result_df['CountryOfResidence'] = result_df['CountryOfResidence'].fillna('')

        # Change 'Postgraduate' to 'PG' and 'Undergraduate' to 'UG' in the 'LoS' column
        #result_df['LoS'] = result_df['LoS'].str.replace('Postgraduate', 'PG')
        #result_df['LoS'] = result_df['LoS'].str.replace('Undergraduate', 'UG')

        # Assign 'Assigned To' based on 'Scored Probabilities'
        df['Assigned To'] = np.where(df['Scored Probabilities'] < 0.22, 'm.brown', 
                                    np.where(df['Scored Probabilities'] < 0.44, 'e.grainger', 'MO.Pending'))

        # Ensure the 'Year' column is a string
        result_df['IntakeYear'] = result_df['IntakeYear'].astype(str)

        # Create 'Task_Description' column
        result_df['Task_Description'] = (
            result_df['intake_status'] + '-' + 
            result_df['IntakeYear'].str[-2:] + '_' + 
            #result_df['InitialOfferStatus'].str.replace('Made Offer', 'MO') + ' ' + 
            result_df['CountryOfResidence']
            # Uncomment the following lines if needed
            # + '_' + result_df['Zone'] 
            # + ' ' + result_df['LoS']
        )

        result_df['TaskCreate'] = result_df['CountryOfResidence'].map(lambda x: 'Yes' if x == 'China' else 'No')
        result_df['Task_Description'] = result_df.apply(lambda x:x['Task_Description'] if x['CountryOfResidence'] == 'China' else '', axis = 1)

        # Add 'tag_date' and 'TaskType' columns
        result_df['tag_date'] = '29/08/2022'

        #Shorten Task Description Concatenation
        result_df['Task_Description']= result_df['Task_Description'].str.replace('Semester ','S')
        result_df['Task_Description']= result_df['Task_Description'].str.replace('Offer ','')

        result_df['TaskType'] = 'Made Offer Campaign'

        if 'Assigned To' not in result_df.columns:
            result_df['Assigned To'] = np.nan  # Initialize with NaN or any default value

        # Now perform the updates
        result_df['Assigned To'] = np.where((result_df['Client'] == 'M') & (result_df['General_Tag'] == 'PT_ENP_TagAXXXX_HIGHXXXX'),'!MO High',result_df['Assigned To'])
        result_df['Assigned To'] = np.where((result_df['Client'] == 'M') & (result_df['General_Tag'] == 'PT_ENP_TagAXXXX_MEDXXXXX'),'!MO Medium',result_df['Assigned To'])
        result_df['Assigned To'] = np.where((result_df['Client'] == 'M') & (result_df['General_Tag'] == 'PT_ENP_TagAXXXX_LOWXXXXX'),'!MO Low',result_df['Assigned To'])
        #add QTAC/UAC to task description
        result_df['Task_Description'] = np.where((result_df['Client'] == 'G') & (result_df['First_agent_tag']=='QTAC') & (result_df['TaskCreate']=='Yes'),result_df['Task_Description']+'_'+result_df['First_agent_tag'],result_df['Task_Description'])
        result_df['Task_Description'] = np.where((result_df['Client'] == 'G') & (result_df['First_agent_tag']=='UAC') & (result_df['TaskCreate']=='Yes'),result_df['Task_Description']+'_'+result_df['First_agent_tag'],result_df['Task_Description'])
            
        result_df.loc[(result_df['TaskCreate'] != 'Yes'),'Assigned To'] = ' '
        result_df.loc[(result_df['TaskCreate'] != 'Yes'),'Task Description'] = ' '
        result_df.loc[(result_df['TaskCreate'] != 'Yes'),'TaskType'] = ' '

        # Assuming 'result_df' is your DataFrame equivalent to 't1' in SQL
        def assign_task_create(row):
            if row['tag_value'] == 'MO_Call_Excluded':
                return 'No'
            elif row['CountryOfResidence'] != 'China':
                return 'No'
            else:
                return 'Yes'

        # Apply the function to each row to create the 'TaskCreate' column
        result_df['TaskCreate'] = result_df.apply(assign_task_create, axis=1)


        # Apply the condition to create the 'Scored Labels' column
        result_df['Scored Labels'] = result_df['Scored Probabilities'].apply(lambda x: "High" if x >= 0.44 else "Low")

        finalColumnList = ['client_id', 'crms_number', 'Client', 'Region', 'Nationality',
       'area_of_study', 'EnrolmentPeriod', 'Age', 'InitialOfferDate',
       'InitialOfferMonth', 'CountryOfResidence', 'Course', 'level', 'faculty',
       'InitialOffer', 'EnrolmentYear', 'tag_value', 'IntakeYear',
       'First_agent_tag', 'intake_status', 'student_status', 'CensusDate'] 
 
        finalColumnList = finalColumnList + ['Scored Labels', 'Scored Probabilities', 'tag_date', 'TaskType','TaskCreate', 'General_Tag', 'Assigned To', 'Task_Description','Task_Description2']
        dfFinal = result_df[finalColumnList].copy()
        return dfFinal
