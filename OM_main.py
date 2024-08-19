import streamlit as st
from sklearn.pipeline import Pipeline
from King.Preprocessing import King_Preprocessing
# from EMEA_OM_King_process import callWebService
import pandas as pd
import json
import base64

#model list for APAC and EMEA
modelList = {'APAC':['GriffDom'],
            'EMEA':['King', 'York']}

#dropdown box
region = st.selectbox('Select a region', ['APAC', 'EMEA'])

#dropdown box
model = st.selectbox("Select a model", modelList[region])

st.title("%s - %s Offer Model"%(region, model))

#widget to upload file
file = st.file_uploader("Upload file", type = ['csv', 'xlsx'])

#selected class of preprocessing
preprocessingDict = {'King': King_Preprocessing()}
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