from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from York.Config import *
import urllib.request
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans

class York_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        scaler = preprocessing.MinMaxScaler()
        gmailList = ['gmai', 'gmaii', 'gmail', 'gamil', 'gmial', 'gmaill', 'gamail', 'googlemail']
        hotmailList = ['homail', 'hotmail', 'live', 'outlook']
        yahooList = ['yahoo', 'yhaoo']
        groupList = ['gmail', 'hotmail', 'yahoo']

        def getDomainGroup(emailDomainArray):
            resultList = []
            
            for emailDomain in emailDomainArray:
                domain = ''
                for no, regexList in enumerate([gmailList, hotmailList, yahooList]):
                    if re.search("|".join(regexList), str(emailDomain)):
                        domain = groupList[no]
                if domain == '':
                    domain = 'others'
                resultList.append(domain) 
            return resultList 

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

        def find_outliers_IQR(df, col):
            #use interquartile range to identify if it is an outlier
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            IQR = q3-q1
            #return True if outlier, else False
            outliersArray = np.where((df[col]<(q1-1.5*IQR))| (df[col]>(q3+1.5*IQR)), True, False)
            #fill in median Age if outlier
            medianAge = np.median(df[col])
            ageArray = np.where(outliersArray, medianAge, df[col])
            return ageArray

        df['EnrolledNumeric'] = 1
        df['Age_Ori'] = df['Age']
        df['Age'] = find_outliers_IQR(df = df, col = 'Age')
        df['Age'] = scaler.fit_transform(df['Age'].values.reshape(-1, 1))
        df['EmailDomainGroup'] = getDomainGroup(df['EmailDomain'].values)
        df['CourseGroup'] = getCourseGroup(df['CourseName'].values)

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

        dfResult['Scored Labels'] = np.where(dfResult['Scored Probabilities'].values> threshold, 1, 0)
        dfResult['General_Tag'] = np.where(dfResult['Scored Labels'] == 1, highTag, lowTag)

        #train and use kmeans
        xCol = 'Scored Probabilities'
        dfTemp = dfResult[dfResult['General_Tag'] == lowTag].copy()
        if dfTemp.shape[0]!=0 and dfTemp.shape[0]!=1:
            num_clusters = 2
            kmeans = KMeans(n_clusters = num_clusters)
            kmeans.fit(dfTemp[[xCol]])

            #assign label
            dfTemp['General_Tag'] = kmeans.labels_
            firstCentroid = kmeans.cluster_centers_[0][0]
            secondCentroid = kmeans.cluster_centers_[1][0]
            if firstCentroid > secondCentroid:
                firstCentroidLabel = mediumTag
                secondCentroidLabel = lowTag
            else:
                firstCentroidLabel = lowTag
                secondCentroidLabel = mediumTag
            centroidDict = {0: firstCentroidLabel, 1: secondCentroidLabel}
            dfTemp['General_Tag'] = dfTemp['General_Tag'].map(centroidDict)

            #concatenate high, med and low 
            dfHigh = dfResult[dfResult['General_Tag'] != lowTag].copy()
            dfResultFinal = pd.concat([dfHigh, dfTemp]).copy()
        else:
            dfResultFinal = dfResult.copy()

        #get back original age
        df = self.df.copy()
        dfResultFinal['Age'] = df['Age_Ori']
        dfResultFinal['tag_date'] = tagDate
        dfResultFinal['TaskType'] = taskType
        dfResultFinal['Tagvalue'] = df['Tagvalue']
        dfResultFinal['TaskCreate'] = np.where(dfResultFinal['Tagvalue'] == 'NULL', "No", "Yes")

        col         = 'General_Tag'
        conditions  = [ dfResultFinal[col] == highTag, dfResultFinal[col] == mediumTag, dfResultFinal[col] == lowTag]
        choices     = [ "HIGH", 'MED', 'LOW' ]
        dfResultFinal['Assigned To'] = np.select(conditions, choices, default=np.nan)
        LoS_Dict = {"Postgraduate":"PG", "Undergraduate":"UG", "Foundation":"F"}

        dfResultFinal['IntakeStatus'] = df['IntakeStatus']
        dfResultFinal['IntakeStatus'] = dfResultFinal['IntakeStatus'].fillna('')
        dfResultFinal['LoS'] = df['LoS']
        dfResultFinal['LoS_ShortForm'] = dfResultFinal['LoS'].map(lambda x:LoS_Dict[x] if x in LoS_Dict.keys() else x)
        dfResultFinal['InitialOfferStatus'] = dfResultFinal['InitialOfferStatus'].map(lambda x:re.sub("Made Offer", "MO", x))
        dfResultFinal['Year'] = df['Year']
        dfResultFinal['Year'] = dfResultFinal['Year'].astype(str).str[-2:]
        dfResultFinal['COR'] = df['COR']
        dfResultFinal['COR'] = np.where(pd.isnull(dfResultFinal['COR']), '', dfResultFinal['COR'])
        dfResultFinal['LoS'] = dfResultFinal['LoS'].map(lambda x:{"Postgraduate":"PG", "Undergraduate":"UG"}.get(x, x))
        dfResultFinal['Task_Description'] = dfResultFinal['IntakeStatus'].astype(str) + '-' + dfResultFinal['Year'] + '_'  +  dfResultFinal['InitialOfferStatus'] \
                                + ' ' + dfResultFinal['COR']  + ' ' + dfResultFinal['LoS_ShortForm']

        #taskCreate = No and task_description empty for COR!=China
        dfResultFinal['TaskCreate'] = dfResultFinal['COR'].map(lambda x: 'Yes' if x == 'China' else 'No')
        dfResultFinal['Task_Description'] = dfResultFinal.apply(lambda x:x['Task_Description'] if x['COR'] == 'China' else '',
            axis = 1)

        finalColumnList = ["AA ClientName", "AA client_id", "AB crms_number","AC_MOTask", "AE_MLTag", 
               "Age", "AgentDirect", "AreaOfStudy", "Campus", "ClientType", "COR", 
               "CORRegion", "CORSubRegion", "CourseName", "Dead", "EmailDomain", 
               "EnrolledNumeric", "EnrPeriod", "Faculty", "FeeStatus", "FirstAgentTag", 
               "FirstStudentStatus", "Gender", "InclusionStatus", "InitialOfferStatus", "IntakeStatus",
               "LoS", "Nationality", "NatRegion", "NatSubRegion", "OfferTagSeq",
               "ProspectType", "Tagvalue", "Year", "Zone", "Number of Records",
               "InitialOfferDate","CensusDate"
               ] + ['Scored Labels', 'Scored Probabilities', 'tag_date', 'TaskType',
                   'TaskCreate', 'General_Tag', 'Assigned To', 'Task_Description',
                   'Tier']
        for col in finalColumnList:
            if col not in dfResultFinal.columns:
                if col in df.columns:
                    dfResultFinal[col] = df[col]
        dfFinal = dfResultFinal[finalColumnList].copy()
        return dfFinal
