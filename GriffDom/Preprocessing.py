from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import re
from GriffDom.Config import *
from category_encoders import TargetEncoder 
from Script.OneHotEncoding import useOneHotEncoder
import json
from sklearn import preprocessing
from sklearn.cluster import KMeans
from datetime import datetime
import openpyxl
import pickle
import xgboost

class GriffDom_Preprocessing(BaseEstimator):
    def __init__(self):
        pass

    def read(self, filename = None):
        if filename:
            wb = openpyxl.load_workbook(filename)
            sheetnameList = wb.sheetnames

            pandasList = []
            for no, sheetname in enumerate(sheetnameList):
                df = pd.read_excel(filename, sheet_name = sheetname)
                df.rename(columns = {"EMAIL_ADDR":"Email", "SAD_TAC_OFFR_YEAR":"Offer Year",
                                'SAD_TAC_OFFR_ROUND':'Offer Round No', 'SAD_TAC_OFFER_PREF':'Offer Pref Nbr',
                                'GU_DESCR120':'Program Description', 'SAD_TAC_OFFR_MONTH':'Offer Month',
                                'ID':"EMPLID"},inplace = True)
                pandasList.append(df)
                
            df = pd.concat(pandasList).copy()
            Source = re.search("(.*).xlsx", filename.name.split('/')[-1]).group(1)
            df['Source'] = Source
            df['Intake'] = re.search("(T\d{1}|Tri (\d{1}))", Source).group(1)
            df['Intake'] = df['Intake'].replace(to_replace = {"Tri ":"T"}, regex = True)
            return df
        
    def fit(self):
        return self

    def transform(self, df = None):
        if 'Offer Dt' in df.columns:
            offerDTCol = "Offer Dt"
        elif 'OFFER_DT' in df.columns:
            offerDTCol = 'OFFER_DT'
       
        df['OfferMonth'] = pd.to_datetime(df[offerDTCol]).dt.strftime('%b').str.upper()
        
        gmailList = ['gmai', 'gmaii', 'gmail', 'gamil', 'gmial', 'gmaill', 'gamail', 'googlemail']
        hotmailList = ['homail', 'hotmail', 'live', 'outlook']
        yahooList = ['yahoo', 'yhaoo']
        groupList = ['gmail', 'hotmail', 'yahoo']

        def getEmailDomainGroup(emailDomainArray):
            resultList = []
            
            for emailDomain in emailDomainArray:
                domain = ''
                for no, regexList in enumerate([gmailList, hotmailList, yahooList]):
                    if re.search("|".join(regexList), str(emailDomain)):
                        domain = groupList[no]
                if domain == '':
                    domain = 'Others'
                resultList.append(domain) 
            return resultList  

        df['Email'] = df['Email'].map(lambda x:str(x).split('@')[1] if re.search('@',str(x)) else x)
        df['EmailDomain'] = getEmailDomainGroup(df['Email'].values)

        def getCourseGroup(courseArray):
            resultList = []
            for value in courseArray:
                if re.search('Engineering', str(value), re.I):
                    group = 'Engineering'
                elif re.search('Law', str(value), re.I):
                    group = 'Law'
                elif re.search('Mathematics', str(value), re.I):  
                    group = 'Mathematics'
                elif re.search('Computer Science|Artifical Intelligence|Information Technology', str(value), re.I):  
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
                elif re.search('Clinical|Public Health|Mental Health|Health Care|Medicine|Immunology|Pharmacy|Health|Physiotherapy|Nutrition and Dietetics|Occupational Therapy|Midwifery', str(value), re.I):  
                    group = 'Med/Health'  
                elif re.search('Business|Finance|Financial Management', str(value), re.I):  
                    group = 'Business/Finance'  
                elif re.search('Nursing', str(value), re.I):  
                    group = 'Nursing'
                elif re.search('Criminology', str(value), re.I):  
                    group = 'Criminal Studies' 
                elif re.search('Social Work|Counselling', str(value), re.I):  
                    group = 'Social Work' 
                elif re.search('Design', str(value), re.I):  
                    group = 'Design' 
                elif re.search('Film|Music', str(value), re.I):  
                    group = 'Film/Music' 
                else:
                    group = 'Others'
                resultList.append(group)
            return resultList
    
        df['CourseGroup'] = getCourseGroup(df['Program Description'].values)
        TargetEncoder = pickle.load(open(TargetEncoderFilename, 'rb'))
        df['ProgramEncoded'] = TargetEncoder.transform(df['Program Description'])
        self.df = df
        #encode features
        # encodedFeatures = encoding(df, colList)

        encoderName = OneHotEncoderFilename
        _, encodedFeatures = useOneHotEncoder(df[colListNeeded], 
                                            savedEncoderName = None,
                                            trainedEncoderName = encoderName)
        testData = xgboost.DMatrix(encodedFeatures)
        return testData

    def finalProcessing(self, body):
        #load trained model
        xgb = xgboost.Booster()
        xgb.load_model(ModelFilename)
        predictions = xgb.predict(body)

        df = self.df
        #create column - client ID, crms_number, general tag
        dfResult = pd.DataFrame()
        dfResult['Client ID'] = "HAU_GRIFFDOM"
        if 'EMPLID' in df.columns:
            dfResult['EMPLID'] = df['EMPLID']
        if 'GU ID' in df.columns:
            dfResult['GU ID'] = df['GU ID']
        dfResult['Intake'] = df['Intake']
        if 'Source' in df.columns:
            dfResult['Source'] = df['Source']
        dfResult['Scored Probabilities'] = predictions
        dfResult['Enrolled'] = np.where(predictions >= threshold, 1, 0)
        dfResult['Client ID'] = "HAU_GRIFFDOM"

        #for general tag
        dfResult['General_Tag'] = np.where(dfResult['Enrolled'] == 1, highLabel, lowLabel)
        lowProbabilities = dfResult.query("General_Tag == '%s'"%lowLabel)['Scored Probabilities'].values

        #train and use kmeans
        xCol = 'Scored Probabilities'
        dfTemp = dfResult[dfResult['General_Tag'] == lowLabel].copy()
        if dfTemp.shape[0]!=0 and dfTemp.shape[0]!=1:
            num_clusters = 2
            kmeans = KMeans(n_clusters = num_clusters)
            kmeans.fit(dfTemp[[xCol]])

            #assign label
            dfTemp['General_Tag'] = kmeans.labels_
            firstCentroid = kmeans.cluster_centers_[0][0]
            secondCentroid = kmeans.cluster_centers_[1][0]
            if firstCentroid > secondCentroid:
                firstCentroidLabel = mediumLabel
                secondCentroidLabel = lowLabel
            else:
                firstCentroidLabel = lowLabel
                secondCentroidLabel = mediumLabel
            centroidDict = {0: firstCentroidLabel, 1: secondCentroidLabel}
            dfTemp['General_Tag'] = dfTemp['General_Tag'].map(centroidDict)

            #concatenate high, med and low 
            dfHigh = dfResult[dfResult['General_Tag'] != lowLabel].copy()
            dfResultFinal = pd.concat([dfHigh, dfTemp]).copy()
        else:
            dfResultFinal = dfResult.copy()

        #other columns - taskcreate
        dfResultFinal['TaskCreate'] = "Yes"
        dfResultFinal['AssignedTo'] = dfResultFinal['General_Tag'].map(lambda x:re.search("(HIGH|MED|LOW)", x).group(1))

        dfResultFinal['Task_Description'] = dfResultFinal['AssignedTo'] + '_' + dfResultFinal['Intake'].str.replace("T", "S")  + '_' + \
                                        "Full_Australia" + '_' + dfResultFinal['Source'].map(lambda x:re.search("(QTAC|UAC)",x).group(1) 
                                                                                if re.search("(QTAC|UAC)",x)
                                                                                else '')
        #special for https://qses.atlassian.net/browse/CS-50542
        # dfResultFinal['Task_Description'] = "March 2024 Nursing Advanced Standing"

        #task description need high/med/low
        dfResultFinal['AssignedTo'] = dfResultFinal["AssignedTo"].map({"HIGH":"!MO High",
                                                            "MED":"!MO Medium",
                                                            "LOW":"!MO Low"})
        #date to finalized the model, change when there is diff version of model
        dfResultFinal['tag_date'] = "19/07/2023"
        dfResultFinal['TaskType'] = dfResultFinal['TaskCreate'].map(lambda x:"Made Offer Campaign" if x == "Yes" else '') 
        return dfResultFinal
