import streamlit as st
# from sklearn.pipeline import Pipeline
from ApacGroupInt.Preprocessing import ApacGroupInt_Preprocessing
from King.Preprocessing import King_Preprocessing
from York.Preprocessing import York_Preprocessing
from Birmingham.Preprocessing import Birmingham_Preprocessing
from Greenwich.Preprocessing import Greenwich_Preprocessing
import pandas as pd
import json
import base64

#model list for APAC and EMEA
modelList = {'APAC':['ApacGroupInt'],
            'EMEA':['King', 'York', 'Birmingham', 'Greenwich']}

#dropdown box
region = st.selectbox('Select a region', ['APAC', 'EMEA'])

#dropdown box
model = st.selectbox("Select a model", modelList[region])

st.title("%s - %s Offer Model"%(region, model))

#widget to upload file
file = st.file_uploader("Upload file", type = ['csv', 'xlsx'])

#selected class of preprocessing
# 'ApacGroupInt':ApacGroupInt_Preprocessing(),
preprocessingDict = {
                    'King': King_Preprocessing(),
                    'York':York_Preprocessing(),
                    'Birmingham':Birmingham_Preprocessing(),
                    'Greenwich':Greenwich_Preprocessing()}
selectPreprocessing = preprocessingDict[model]

#set up pipeline
# modelPipeline = Pipeline([
#                             ('preprocess', selectPreprocessing)
#                         ])

#function to read file
# @st.cache(suppress_st_warning = True, allow_output_mutation=True)
# @st.cache_data()
def load_data(file_uploaded):
    if '.xlsx' in file_uploaded.name:
        return pd.read_excel(file_uploaded)
    elif '.csv' in file_uploaded.name:
        return pd.read_csv(file_uploaded, sep = ',', encoding = 'utf-8')

if file:
    st.markdown("Uploaded filename: %s"%file.name)
    df = load_data(file)

    try:
        body = selectPreprocessing.transform(df)
        dfResult = selectPreprocessing.finalProcessing(body)
        result = 1
        st.markdown("Model run is completed. Please download result")
    except Exception as e:
        print(e)
        st.markdown(e)
        result = 0

        #if there is a result
    if result == 1:
        # if '.xlsx' in file.name:
        #     # resultLoc2 = resultLoc + '.xlsx'
        #     # fileStr = dfResult.to_excel(index = False)
        #     # fileformat = 'xlsx'
        #     fileStr = dfResult.to_csv(index = False)
        #     fileformat = 'csv'  
        # elif '.csv' in file.name:
        #     # resultLoc2 = resultLoc + '.csv'
        #     fileStr = dfResult.to_csv(index = False)
        #     fileformat = 'csv'       
        # b64 = base64.b64encode(fileStr.encode()).decode()  # some strings <-> bytes conversions necessary here
        # href = f'<a href="data:file/csv;base64,{b64}">Download CSV File</a> (right-click and save link as &lt;name&gt;.%s)'%fileformat
        # st.markdown(href, unsafe_allow_html=True)

        csv = dfResult.to_csv(index = False).encode('utf-8')
        st.download_button(
        "Press to download",
        csv,
        file_name = "Result.csv",
        mime = "text/csv",
        key = 'download'
        )
