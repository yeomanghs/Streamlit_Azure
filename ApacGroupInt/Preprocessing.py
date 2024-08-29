from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from ApacGroupInt.Config import *
import urllib.request
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans
from datetime import datetime

class ApacGroupInt_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
        # Convert 'InitialOfferDate' to datetime
        df['InitialOfferDate'] = pd.to_datetime(df['InitialOfferDate'], format="%Y-%m-%d")

        # Create 'Enrolment_Date' by concatenating 'EnrolmentPeriod' and 'EnrolmentYear'
        df['Enrolment_Date'] = df['EnrolmentPeriod'] + " " + df['EnrolmentYear'].astype(str)

        # Perform a left join with Date_data on 'Enrolment_Date'
        Date_data = pd.read_csv(filename_Date)
        dfMerge = pd.merge(df, Date_data, how='left', on='Enrolment_Date')

        # Convert 'InitialOfferDate' to string and then to datetime
        dfMerge['InitialOfferdate_1'] = pd.to_datetime(dfMerge['InitialOfferDate'].astype(str))

        # Convert 'EnrolmentDate' to datetime with the specified format
        dfMerge['EnrolmentDate'] = pd.to_datetime(dfMerge['EnrolmentDate'], format="%d/%m/%Y")

        # Calculate the recency time difference in days
        dfMerge['Recency_time'] = (dfMerge['EnrolmentDate'] - dfMerge['InitialOfferdate_1']).dt.days

        # Apply recency categories based on the calculated 'Recency_time'
        def recency_category(days):
            if days >= 130:
                return "PAST"
            elif days >= 88:
                return "RECENT"
            elif days > 0:
                return "MOST RECENT"
            else:
                return "NEGATIVE"

        dfMerge['Recency'] = dfMerge['Recency_time'].apply(recency_category)

        # Determine the student type based on 'CountryOfResidence'
        dfMerge['StudentType'] = dfMerge['CountryOfResidence'].apply(lambda x: "Domestic" if x == "Australia" else "International")

        df = dfMerge.copy()
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

        df['Scored Labels'] = dfResult['Scored Labels']
        df['Scored Probabilities'] = dfResult['Scored Probabilities']
        # General_Tag creation
        df['General_Tag'] = df['Scored Probabilities'].apply(
            lambda x: lowTag if x < 0.08 else (mediumTag if x < 0.15 else highTag)
        )

        # Task_Description2 creation
        df['Task_Description2'] = df.apply(
            lambda row: (
                'LOW_' + row['EnrolmentPeriod'] + '_' + str(row['IntakeYear']) + '_' + row['InitialOffer'] + '_' + row['CountryOfResidence']
                if row['Scored Probabilities'] < 0.08 else
                'MED_' + row['EnrolmentPeriod'] + '_' + str(row['IntakeYear']) + '_' + row['InitialOffer'] + '_' + row['CountryOfResidence']
            ) if row['Scored Probabilities'] < 0.15 else
            'HIGH_' + row['EnrolmentPeriod'] + '_' + str(row['IntakeYear']) + '_' + row['InitialOffer'] + '_' + row['CountryOfResidence'],
            axis=1
        )

        # TaskCreate creation
        df['TaskCreate'] = df['tag_value'].apply(
            lambda x: 'No' if x == 'MO_Call_Excluded' else 'Yes'
        )

        # Task_Description creation
        df['Task_Description'] = df.apply(
            lambda row: '' if row['tag_value'] == 'MO_Call_Excluded' else row['Task_Description2'],
            axis=1
        )

        # TaskType creation
        df['TaskType'] = df['tag_value'].apply(
            lambda x: '' if x == 'MO_Call_Excluded' else 'Made Offer Campaign'
        )

        # Adding 'tag_date' column
        df['tag_date'] = "29/8/2022"

        # Shorten Task Description Concatenation
        df['Task_Description'] = df['Task_Description'].str.replace('Semester ', 'S')
        df['Task_Description'] = df['Task_Description'].str.replace('Offer ', '')

        # Join with task assignment table to generate "Assigned To" based on country
        Task_AssignmentMapData = pd.read_csv(filename_Task_Assignment)
        df = df.merge(Task_AssignmentMapData, how='left', left_on='CountryOfResidence', right_on='COR')

        #Assigned to high, med, or low queue for clients that don't have regional queues (E & W)
        df.loc[(df['tag_value'] != 'MO_Call_Excluded')&(df['General_Tag'] == 'PT_ENP_TagAXXXX_HIGHXXXX'),'Assigned'] 
        df.loc[(df['tag_value'] != 'MO_Call_Excluded')&(df['General_Tag'] == 'PT_ENP_TagAXXXX_MEDXXXXX'),'Assigned'] 
        df.loc[(df['tag_value'] != 'MO_Call_Excluded')&(df['General_Tag'] == 'PT_ENP_TagAXXXX_LOWXXXXX'),'Assigned'] 
        df.loc[(df['TaskCreate'] != 'Yes'),'Assigned'] = ' '

        # Update the 'Scored Labels' column based on the `Scored Probabilities`
        df['Scored Labels'] = df['Scored Probabilities'].apply(
            lambda x: 'High' if x >= 0.15 else 'Low'
        )

        finalColumnList = ['client_id', 'crms_number', 'Client', 'Region', 'Nationality', 'area_of_study', 
                        'EnrolmentPeriod', 'Age', 'InitialOfferDate', 'InitialOfferMonth', 'CountryOfResidence', 
                        'Course', 'level', 'faculty', 'InitialOffer', 'EnrolmentYear', 'tag_value', 'IntakeYear', 
                        'First_agent_tag', 'intake_status', 'student_status'

                    ] + ['Scored Labels', 'Scored Probabilities', 'General_Tag', 'TaskCreate', 
                        'Task_Description', 'TaskType', 'tag_date', 'Assigned']
        dfFinal = df[finalColumnList].copy()
        return dfFinal
