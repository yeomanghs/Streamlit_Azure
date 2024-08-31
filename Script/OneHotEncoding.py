
import pickle
from sklearn.preprocessing import OneHotEncoder
import pandas as pd
import numpy as np

def useOneHotEncoder(df, savedEncoderName, trainedEncoderName = None):
    #select qualitative columns
    qualiColList = [i for i in df.columns if df[i].dtypes == "object"]
    
    #if use trainedEncoder
    if trainedEncoderName:
        categorical_encoder = pickle.load(open(trainedEncoderName, 'rb'))
        dfQualiDummy = categorical_encoder.transform(df[qualiColList])
    else:
        #new encoder
        categorical_encoder = OneHotEncoder(handle_unknown='ignore')
        dfQualiDummy = categorical_encoder.fit_transform(df[qualiColList])
        #save encoder
        filename = savedEncoderName
        with open(filename, "wb") as f: 
            pickle.dump(categorical_encoder, f)
        print(f"Encoder is saved as {savedEncoderName}")
            
    # dfTemp = pd.DataFrame.sparse.from_spmatrix(dfQualiDummy,
    #                                            columns = categorical_encoder.get_feature_names(qualiColList))
    dfTemp = pd.DataFrame.sparse.from_spmatrix(dfQualiDummy,
                                               columns = categorical_encoder.get_feature_names_out(qualiColList))
    dfModel = df[[i for i in df.columns if i not in qualiColList]]
    dfModel.reset_index(drop = True, inplace = True)
    dfX = pd.concat([dfTemp, 
                     dfModel],
                   axis = 1).copy()

    # Convert to numpy array
    features = np.array(dfX)
    
    return dfX, features
