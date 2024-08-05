import streamlit as st
from EMEA_OM_King_config import *
from EMEA_OM_King_process import callWebService
import pandas as pd
import json
import base64

#widget to upload file
file = st.file_uploader("Upload file", type = ['csv', 'xlsx'])

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
    df['Enrolled'] = 1

    #if all columns needed are found in df
    allColumnsNeeded = colListNeeded
    if len(set(df.columns) & set(allColumnsNeeded)) == len(allColumnsNeeded):
        st.markdown("All columns needed are found")

        try:
            sample_records = df[[i for i in allColumnsNeeded]].to_dict('records')

            body = str.encode(json.dumps(sample_records))
            headers = {'Content-Type':'application/json'}

            result = callWebService(url = url, body = body, headers = headers)
            resultJson = json.loads(json.loads(result))
            dfResult = pd.DataFrame(resultJson['result'], columns = allColumnsNeeded + ['Scored Labels', 'Scored Probabilities'])
            result = 1
            st.markdown("Model run is completed. Please download result")
        except Exception as e:
            print(e)
            result = 0
    else:
        st.markdown("Columns not found: %s" %(set(allColumnsNeeded).difference(set(df.columns))))
        result = 0 

        #if there is a result
    if result == 1:
        if '.xlsx' in file.name:
            # resultLoc2 = resultLoc + '.xlsx'
            # fileStr = dfResult.to_excel(index = False)
            # fileformat = 'xlsx'
            fileStr = dfResult.to_csv(index = False)
            fileformat = 'csv'  
        elif '.csv' in file.name:
            # resultLoc2 = resultLoc + '.csv'
            fileStr = dfResult.to_csv(index = False)
            fileformat = 'csv'       
        b64 = base64.b64encode(fileStr.encode()).decode()  # some strings <-> bytes conversions necessary here
        href = f'<a href="data:file/csv;base64,{b64}">Download CSV File</a> (right-click and save link as &lt;name&gt;.%s)'%fileformat
        st.markdown(href, unsafe_allow_html=True)