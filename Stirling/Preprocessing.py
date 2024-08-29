from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from Stirling.Config import *
import urllib.request
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans

class Stirling_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df

        def getCourseGroup(courseArray):
            resultList = []
            for value in courseArray:
                if re.search('Engineering', str(value), re.I):
                    group = 'Engineering'
                elif re.search('Law', str(value), re.I):
                    group = 'Law'
                elif re.search('Mathematics', str(value), re.I):  
                    group = 'Mathematics'
                elif re.search('Computer Science|Artifical Intelligence', str(value), re.I):  
                    group = 'IT' 
                elif re.search('English|Modern Languages|Linguistics|Creative Writing|Translation Studies|French|German|Spanish', str(value), re.I):  
                    group = 'English/Language'  
                elif re.search('Economics', str(value), re.I):  
                    group = 'Economics'  
                elif re.search('Geology|Science|Biology|Physics|Biotechnology|Biochemistry|Chemistry|Geography', str(value), re.I):  
                    group = 'Science'  
                elif re.search('Shakespeare|Philosophy|History|Art|Literature and Culture', str(value), re.I):  
                    group = 'Literature/Philosophy' 
                elif re.search('Psychology', str(value), re.I):  
                    group = 'Psychology'  
                elif re.search('Education|Teaching', str(value), re.I):  
                    group = 'Education'
                elif re.search('Clinical|Public Health|Mental Health|Health Care|Medicine|Immunology|Pharmacy|Health', str(value), re.I):  
                    group = 'Med/Health'  
                elif re.search('Business|Finance|Financial Management', str(value), re.I):  
                    group = 'Business/Finance'  
                else:
                    group = 'Others'
                resultList.append(group)
            return resultList

        df['CourseGroup'] = getCourseGroup(df['CourseName'].values)
            
        #date-related feature
        df['InitialOfferMonth'] = pd.to_datetime(df['InitialOfferDate'], format='%d/%m/%Y').dt.month.astype(str)
            
        dayDict = {0:"Monday", 1:"Tuesday", 2:"Wednesday", 3:"Thursday", 4:"Friday", 5:"Saturday", 6:"Sunday"}

        df['InitialOfferDay'] = pd.to_datetime(df['InitialOfferDate'], format='%d/%m/%Y').dt.weekday.map(dayDict)

        df['IsInitialOfferWeekDay'] = df['InitialOfferDay'].map(lambda x:x not in ['Saturday', 'Sunday'])

        df['Semester'] = df['EnrPeriod'].str[:10]

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
        tagDate = "19/09/2023"
        taskType = 'Made Offer'
        df = self.df.copy()
        df['Scored Labels'] = dfResult['Scored Labels']
        df['Scored Probabilities'] = dfResult['Scored Probabilities']

        # Equivalent of CASE statement in SQL
        df['General_Tag'] = np.where(
            df['Scored Probabilities'] < 0.22,
            np.where(
                df['Scored Probabilities'] < 0.11,
                'PT_ENP_TagAXXXX_LOWXXXXX',
                'PT_ENP_TagAXXXX_MEDXXXXX'
            ),
            'PT_ENP_TagAXXXX_HIGHXXXX'
        )

        # Handling NA values in the COR column
        df['COR'] = np.where(df['COR'].isna(), "", df['COR'])

        # Replacing 'Postgraduate' with 'PG' and 'Undergraduate' with 'UG' in the LoS column
        df['LoS'] = df['LoS'].str.replace('Postgraduate', 'PG')
        df['LoS'] = df['LoS'].str.replace('Undergraduate', 'UG')

        # Assigning 'LOW', 'MED', or 'HIGH' based on Scored Probabilities
        df['Assigned To'] = np.where(
            df['Scored Probabilities'] < 0.11, 
            'LOW', 
            np.where(df['Scored Probabilities'] > 0.22, "HIGH", "MED")
        )

        # Creating Task_Description2 using multiple columns
        df['Task_Description2'] = (
            df['IntakeStatus'] + '-' +
            df['Year'].astype(str).str[-2:] + "_" +
            df['Zone'] + " " +
            df['InitialOfferStatus'].str.replace('Made Offer', 'MO') + " " +
            df['COR'] + " " +
            df['LoS']
        )

        # Adding a tag_date and TaskType columns
        df['tag_date'] = "19/09/2023"
        df['TaskType'] = 'Made Offer'

        # Handling TaskCreate column based on Tagvalue and COR columns
        df['TaskCreate'] = np.where(
            (df['Tagvalue'] == 'MO_Call_Excluded') | (df['COR'] != 'China'),
            'No',
            'Yes'
        )

        # Handling Task_Description based on Tagvalue and COR columns
        df['Task_Description'] = np.where(
            (df['Tagvalue'] == 'MO_Call_Excluded') | (df['COR'] != 'China'),
            '',
            df['Task_Description2']
        )

        # Creating a Scored Labels column based on Scored Probabilities
        df['Scored Labels'] = np.where(df['Scored Probabilities'] < 0.11, 0, 1)

        finalColumnList = ["AA ClientName", "AA client_id", "AB crms_number","AC_MOTask", "AE_MLTag", 
               "Age", "AgentDirect", "AreaOfStudy", "Campus", "ClientType", "COR", 
               "CORRegion", "CORSubRegion", "CourseName", "Dead", "EmailDomain", 
               "EnrolledNumeric", "EnrPeriod", "Faculty", "FeeStatus", "FirstAgentTag", 
               "FirstStudentStatus", "Gender", "InclusionStatus", "InitialOfferStatus", "IntakeStatus",
               "LoS", "Nationality", "NatRegion", "NatSubRegion", "OfferTagSeq",
               "ProspectType", "Tagvalue", "Year", "Zone", "Number of Records",
               "InitialOfferDate","CensusDate"
               ] + ['Scored Labels', 'Scored Probabilities', 'tag_date', 'TaskType',
                   'TaskCreate', 'General_Tag', 'Assigned To', 'Task_Description']
        dfFinal = df[finalColumnList].copy()
        return dfFinal
