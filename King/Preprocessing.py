from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from King.Config import *
import urllib.request
import json

class King_Preprocessing(BaseEstimator):
    def __init__(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if isinstance(df, pd.DataFrame):
            self.df = df
        df['Enrolled'] = 1

        #fill in missing values for categorical columns
        categoricalColList = ['CORRegion','Nationality',
                                'InitialOfferStatus',
                                'COR','LoS','Faculty','CourseName']
        for col in categoricalColList:
            df[col] = df[col].fillna('')

        #fill in missing values for numerical column - Age with median
        df['Age'] = df['Age'].fillna(0)
        medianAge = df[df['Age']!='NULL']['Age'].astype(float).median()
        df['Age'] = df['Age'].map(lambda x:medianAge if x == 'NULL' else float(x))
        df['Age'] = df['Age'].map(lambda x:medianAge if x >= 100 else x)

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
        #predefine parameters or from config
        # threshold = 0.2
        medium_threshold = 0.14
        highTag = "PT_ENP_TagAXXXX_HIGHXXXX"
        mediumTag = "PT_ENP_TagAXXXX_MEDXXXXX"
        lowTag = "PT_ENP_TagAXXXX_LOWXXXXX"
        tagDate = "09/06/2022"
        taskType = 'Made Offer'

        #Update df by adding tag_date, TaskCreate, TaskType Columns
        df = self.df.copy()
        df['tag_date'] = tagDate
        df['TaskType'] = taskType
        df['TaskCreate'] = np.where(df['Tagvalue'] == 'NULL', "No", "Yes")

        #assign Scored_Labels and General_Tag based on Scored Probabilities
        df['Scored Probabilities'] = dfResult['Scored Probabilities']
        df['Scored Labels'] = np.where(df['Scored Probabilities'].values>=threshold, 1, 0)
        df['General_Tag'] = np.where(df['Scored Labels'] == 1, highTag, lowTag)
        lowProbabilities = df.query("General_Tag == '%s'"%lowTag)['Scored Probabilities'].values

        #assign medium group based on medium_threshold
        df['General_Tag'] = df.apply(lambda x:mediumTag if x['General_Tag'] == lowTag
                                    and x['Scored Probabilities'] >= medium_threshold else x['General_Tag'], axis = 1)
        #for task description
        df['General_TagType'] = df['General_Tag'].map(lambda x:re.search("(HIGH|LOW|MED)",x).group(1))
        LoS_Dict = {"Postgraduate":"PG", "Undergraduate":"UG", "Foundation":"F"}
        df['LoS_ShortForm'] = df['LoS'].map(lambda x:LoS_Dict[x] if x in LoS_Dict.keys() else '')
        df['InitialOfferStatus'] = df['InitialOfferStatus'].map(lambda x:re.sub("Made Offer", "MO", x))
        df['Year'] = df['Year'].astype(str).str[-2:]
        df['Campus'] = df['Campus'].map(lambda x:'' if x=='NULL' else x)
        df['COR'] = np.where(pd.isnull(df['COR']), '', df['COR'])
        df['LoS'] = df['LoS'].map(lambda x:{"Postgraduate":"PG", "Undergraduate":"UG"}.get(x, x))

        col         = 'Scored Probabilities'
        conditions  = [ df[col] > threshold, (df[col] < threshold) & (df[col]> medium_threshold), df[col] <= medium_threshold ]
        choices     = [ "HIGH", 'MED', 'LOW' ]
        df['Assigned To'] = np.select(conditions, choices, default=np.nan)
        #task description column
        #task description from EMEA Group 1 OM IntakeStatus ||'-'||substr(Year, -2)||' '||'_HIGH'||' '||Replace(InitialOfferStatus, 'Made Offer', 'MO')||' '||COR||' '||Campus||' '||Replace(Replace(LoS, 'Postgraduate', 'PG'), 'Undergraduate', 'UG')
        #assume intakeStatus(Sep, Jan and etc) = IntakeMonth
        #General_TagType is HIGH/LOW/MED
        #campus col is empty
        #tag_value = 'NULL' is equivalent to Tagvalue = 'MO_Call_Excluded'
        #  
        df['Zone'] = ''
        # df['Task_Description'] = df['IntakeStatus'].astype(str) + '-' + df['Year'] + '_' + df['General_TagType'] + ' ' +  df['InitialOfferStatus'] + ' ' + df['COR']  + ' ' + df['Campus'] + ' ' + df['LoS_ShortForm']
        def getTier(corArray, LosArray):
            resultList = []
            for no, cor in enumerate(corArray):
                if cor in ['India']:
                    tier = '1'
                elif cor in ['United States', 'Canada']:
                    tier = '2'
                elif cor in ['Saudi Arabia', 'United Arab Emirates', 'Malaysia', 'Hong Kong', 'Singapore']:
                    tier = '3'
                elif cor in ["Russian Federation",  "Germany", "United Kingdom", "France", "Italy", 
                            "Spain", "Ukraine", "Poland", "Romania",
                            "Netherlands", "Belgium", "Czech Republic", "Greece","Portugal",
                            "Sweden",  "Hungary",'Belarus', "Austria","Serbia",
                            "Switzerland",'Bulgaria', "Denmark","Finland", "Slovakia",
                            "Norway", "Ireland", "Croatia","Moldova","Bosnia and Herzegovina", 
                            "Albania","Lithuania",  "Macedonia, the former Yugoslav Republic of","Slovenia","Latvia", 
                            "Estonia","Montenegro", "Luxembourg","Malta","Iceland",
                            "Andorra", 'Monaco',"Liechtenstein","San Marino",'Holy See (Vatican City State)', 'China']:
                    if cor == 'China':
                        if LosArray[no] == 'UG':
                            tier = 'CTI'
                        else:
                            tier = ''
                    else:
                        tier = 'CTI'
                else:
                    tier = ''
                resultList.append(tier)
            return resultList

        df['Tier'] = getTier(df['COR'].values, df['LoS_ShortForm'].values) 

    #from r modules
    # dataset1$Task_Description = ifelse(dataset1$Tier == '',
    #     paste(dataset1$IntakeStatus,'-',str_sub(dataset1$Year, -2,-1),"_",dataset1$Zone," ",str_replace(dataset1$InitialOfferStatus, 'Made Offer', 'MO'), " ", dataset1$COR, " ", dataset1$LoS_ShortForm,sep=""),
    #     paste(dataset1$Tier, '_',dataset1$IntakeStatus,'-',str_sub(dataset1$Year, -2,-1),"_",dataset1$Zone," ",str_replace(dataset1$InitialOfferStatus, 'Made Offer', 'MO'), " ", dataset1$COR, " ", dataset1$LoS_ShortForm,sep=""))
        def getTaskDescription(x):
            if x['Tier'] == '':
                result = str(x['IntakeStatus']) + '-' + str(x['Year']) + '_' + str(x['Zone'])\
                        + ' ' + re.sub('Make Offer', 'MO', str(x['InitialOfferStatus'])) + ' '\
                        + str(x['COR']) + ' ' + str(x['LoS_ShortForm'])
            else:
                result = str(x['Tier']) + '_' + str(x['IntakeStatus']) + '-' + str(x['Year']) + '_' + str(x['Zone'])\
                + ' ' + re.sub('Make Offer', 'MO', str(x['InitialOfferStatus'])) + ' '\
                + str(x['COR']) + ' ' + str(x['LoS_ShortForm'])
            return result
        df['Task_Description'] = df.apply(getTaskDescription, axis = 1)

        #from r modules
        # dataset1$Task_Description = ifelse(dataset1$COR == 'China',dataset1$Task_Description, '')
        # dataset1$TaskCreate = ifelse(dataset1$COR == 'China','Yes', 'No')

        df['Task_Description'] = df.apply(lambda x:x['Task_Description'] if x['COR'] == 'China' else '', axis = 1)
        df['TaskCreate'] = df.apply(lambda x:'Yes' if x['COR'] == 'China' else 'No', axis = 1)

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
        dfFinal = df[finalColumnList].copy()
        return dfFinal
