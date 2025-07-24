import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title('CloudWalk Data Analyst Case')

df = pd.read_pickle('data.gz')

st.dataframe(df)

