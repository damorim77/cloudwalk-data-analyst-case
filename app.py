import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import humanize
import numpy as np

from toc import Toc
from datalayer import DataLayer

st.set_page_config(layout="wide", page_title='CloudWalk Data Analyst Case')

toc = Toc()
dl = DataLayer()

st.title('CloudWalk Data Analyst Case')

with st.spinner("Loading data ⏳"):

    df = dl.df
    meta = dl.meta
    dfu = dl.load_unpivoted()
    dfg = dl.load_with_share()

# st.dataframe(dfg, hide_index=True)


aux_date_cohort = df[['date','cohort']].copy()

df['cohort'] = df['cohort'].dt.strftime('%Y-%m')
df['date'] = df['date'].dt.strftime('%Y-%m')


with st.container(border=True):
    st.header("Table of contents")
    toc.placeholder()





with st.container(border=True):
    toc.header("1. Intro")
    st.markdown("""
        This app was developed by Danilo Amorim in order to provide visual aid for the CloudWalk Data Analyst case.   
        Below is a sample of the data for the challenge
    """)

    st.dataframe(df, hide_index=True)





with st.container(border=True):
    toc.header("2. Premises")

    st.markdown("""
    Below are described some premises that might affect the analysis of the dataset:  
    *(based on my personal interpretations of the dataset structure and business rules)*

    - The dataset profile might be described as a cohort-based time series of end-of-month aggregated data per merchant segment.
    - The time series start on jan/24 with the first cohort of registered customers. There are no cohorts older than that. So, older customers are out of scope of this study.
    - Also, given that the first customer cohort is registered by jan/24, and the merchant segmentation rule is based on last 90 day behaviour, it is only possible to measure quantity of inactive customers starting from apr/24.
    - Merchant's segmentation rule allows merchants to flow through different segments between months according to their product category usage behaviour. So, a single merchant does not necessarily preserves the same segment from the previous month to the next one. But with the given dataset is not possibile to precisely map how many customers migrated from one segment to another between months.
    - Merchant's segmentation rule is a tree-like segmentation that might shadow the true quantity of active customers on bottom-level product categories. For example, should a merchant use both 'tap to pay' and 'POS' solutions within the 90-day period, the merchant is categorized as 'SMB' although he is also an active user of the 'tap to pay' solution.            
                """)




with st.container(border=True):

    toc.header("3. Dataset preparation")

    toc.subheader("Adding columns to calculate average of financial values per merchant segment")
    st.markdown("""
    - These columns will help analyze average ticket (R$) spent per merchant segment, per product           
    - For banking product, it was chosen to take average for all columns (balance, cashin and cashout)  
    
    Calculation formula (applied per product): 
    """)
    st.code("Avg Ticket (R$) = Total spent (R$) / Qty merchants (n)", language='excelFormula')


    column_map = {
        'transacted_amount': 'acquiring_merchants',
        'account_balance': 'banking_merchants',
        'account_cashin': 'banking_merchants',
        'account_cashout': 'banking_merchants',
        'infinitecard_transacted_amount': 'infinitecard_merchants',
        'smartcash_amount_lent': 'smartcash_merchants',
        'pix_credit_lent': 'pix_credit_merchants'
    }

    for money_col, qty_col in column_map.items():
        df[ f"avg_{money_col}" ] = df[money_col] / df[qty_col]

    st.dataframe(
        df[['date','cohort','segment'] + [c for c in df.columns if 'avg_' in c] ].sample(10) ,
        hide_index=True
    )

    toc.subheader("Adding a new calculated column: months_since_register")
    st.markdown("""
    - The purpose of this column is to aggregate merchants that are InfinitePay customers for the same amount of time, regardless of the register date
    - The hypothesis is that merchants that are customers for the same amount of time might be in the same stage of maurity on a customer lifecycle, thus exhibiting similar behaviour patterns

    Calculation formula: 
    """)
    st.code("months_since_register = (date - cohort) // 30", language='excelFormula')            

    df['months_since_register'] = (aux_date_cohort['date'] - aux_date_cohort['cohort']).dt.days // 30

    st.dataframe(df[['date','cohort','months_since_register']].sample(10), hide_index=True)




with st.container(border=True):

    toc.header("4. Analysis")

    toc.subheader("Cohort Analyis")

    st.markdown("""
    The goal is to analyze each cohort evolution accross all metrics and merchant segments over time.  
    Notes: 
    - **ALL** segment refers to the grouping of all merchants regardless of the segment
    - **ALL_ACTIVE** segment refers to the grouping of all merchants except 'inactive'  

    **Please select a metric and a segment to visualize**
    """)

    @st.fragment
    def render_cohort():
        #@title Cohort Heatmap

        cols = st.columns([1,2,2])

        metric =  cols[0].selectbox(
            "Metric" ,
            [
                "transacted_amount",
                "acquiring_merchants",
                "account_balance",
                "account_cashin",
                "account_cashout",
                "banking_merchants",
                "infinitecard_transacted_amount",
                "infinitecard_merchants",
                "smartcash_amount_lent",
                "smartcash_merchants",
                "pix_credit_lent",
                "pix_credit_merchants",
                "avg_transacted_amount",
                "avg_account_balance",
                "avg_infinitecard_transacted_amount",
                "avg_smartcash_amount_lent",
                "avg_pix_credit_lent"
            ]
        )  
        segment = cols[1].segmented_control(
            "Segment" , 
            ["ALL", "ALL_ACTIVE", "SMB", "micro", "card_not_present","inactive"] ,
            default="ALL",
            selection_mode="single"
        )


        aux = df.copy()
        if segment == 'ALL_ACTIVE':
            aux = aux[ aux.segment != 'inactive' ]
        elif segment != 'ALL':
            aux = aux[ aux.segment == segment ]

        cross_tab = pd.crosstab(
            index=aux['cohort'],
            columns=aux['date'],
            values=aux[metric],
            aggfunc='sum'
        )

        def try_humanize(x):
            try:
                n = humanize.intword(int(x))            
                n = n.replace("thousand","k")
                n = n.replace("million","M")
                return n
            except:
                return ""

        text_matrix = cross_tab.applymap(try_humanize)

        fig = px.imshow(
            cross_tab, 
            color_continuous_scale= px.colors.diverging.Temps_r,
            labels = dict(
                x='Month',
                y='Cohort',
                color=metric
            ),
            # text_auto=True
        )

        fig.update_traces(
            text=text_matrix.values,
            texttemplate="%{text}", 
            textfont_size=10 
        )

        fig.update_layout(
            height=700, 
            margin=dict(l=0, r=0, b=0, t=0, pad=4),            
        )

        st.plotly_chart(fig, use_container_width=True)

    render_cohort()



    toc.subheader("Product preference analysis")
    st.markdown(""" 
    Product preference is an inference of which product a customer chooses more over other options available.   
    This is particularly difficult to measure on financial services because it's often unclear what it means "to choose more".    
    We might consider as a measure of preference:
    1. How much money customers allocated on a particular service, but also 
    2. How many customers allocated any amount of money on that particular service.  

    The problem with the first measure is that it is biased towards customers with higher acquisition power, thus representing the preference of a few, but the second, might not present enough financial relevance for the business.  
    In that sense, a more parcimonious measure to encompass both needs is the **average ticket per customer**.  
    By dividing the total amount of money by the number of customers, we get a rough estimate of how much money we might expect a single customer might spend on that product.  
    This way, the measure does not overprivilege higher acquisition power customers, nor disregard the financial relevance for the business whatsoever.  
    Besides, this measure works nicely as a proxis to profitability per customer.
                
    The next charts take all these concerns into account.     
    """)


    @st.fragment
    def render_preference_charts(aux):

        segment = st.segmented_control(
            "Segment" , 
            ["ALL", "ALL_ACTIVE", "SMB", "micro", "card_not_present","inactive"] ,
            default="ALL",
            selection_mode="single",
            key='segment_v2'
        )

        if segment == 'ALL_ACTIVE':
            aux = aux[ aux.segment != 'inactive' ]
        elif segment != 'ALL':
            aux = aux[ aux.segment == segment ]

        color_scale = px.colors.qualitative.Bold
        
        color_discrete_map = {
            'acquiring': color_scale[0],
            'banking': color_scale[1],
            'infinitecard': color_scale[2],
            'pixcredit': color_scale[3],
            'smartcash': color_scale[4]
        }

        with st.spinner("Loading visualization ⏳"):

            st.markdown("##### Evolution of total amount and merchants per product and segment over time")
            st.markdown("""
               This chart presents the relation of number of merchants and total amount spent, over time, per segment and product.   
                The bubble sizes are the average ticket spent.
            """)
            st.markdown("**Click the play icon [▶️] to visualize evolution of over time.**")

            fig = px.scatter(
                aux, 
                x="total_amount", 
                y="total_merchants", 
                animation_frame="date", 
                animation_group="segment",
                size="avg_ticket",
                text='segment' if aux.segment.nunique() > 1 else 'product',
                color="product",
                hover_name="segment",
                log_x=True, 
                log_y=True, 
                size_max=55, 
                range_x=[0.1, aux['total_amount'].max() * 1.5 ], 
                range_y=[0.1, aux['total_merchants'].max() * 1.5],
                color_discrete_map=color_discrete_map
            )
            fig.update_layout(
                height=400, 
                transition = { 'duration': 50_000 },
                margin=dict(l=0, r=0, b=20, t=0, pad=4),
            )
            fig.update_traces(textfont=dict(size=10))


            st.plotly_chart(fig)


            st.markdown("##### Ranking of product preference over time")
            st.markdown("""
               This chart ranks the most prefered products over time, according to average ticket spent on the refered period
            """)

            aux = dfg[  dfg.segment == segment ]

            fig = go.Figure()

            for prod in aux['product'].unique():

                aux_prod = aux [  aux['product'] == prod ]
                current_color = color_discrete_map.get(prod, 'gray')
                
                fig.add_trace(
                    go.Scatter(
                        x = aux_prod['date'] ,
                        y = list(aux_prod['rank']) ,
                        mode = 'lines+markers',
                        name = prod ,
                        text =  [f"{t:.2%}" for t in aux_prod['percent_avg_ticket']]  ,
                        textposition="top center" ,
                        marker = dict(size=20, color=current_color),
                        line=dict(color=current_color)
                    )
                )

            fig.update_layout(
                height = 250,
                yaxis=dict(autorange='reversed'), 
                margin=dict(l=0, r=0, b=20, t=0, pad=4),
            )

            st.plotly_chart(fig)

            st.markdown("##### Share of product preference over time")
            st.markdown("""
               This chart presents how much a product was prefered over time, according to the share of average ticket spent.
            """)

            fig = px.bar(
                aux ,
                x ='date',
                y ='percent_avg_ticket',
                range_y=[0,1],
                barmode='relative',
                color = 'product',
                color_discrete_map=color_discrete_map ,
                text = 'percent_avg_ticket'
            )

            fig.update_layout(
                height = 250,
                margin=dict(l=0, r=0, b=20, t=0, pad=4),
                yaxis_title=None,
                yaxis=dict(
                   tickformat=".0%"  # Formats as percentage with no decimal places
                ),
                xaxis_title=None,
            )

            fig.update_traces(texttemplate='%{text:.1%}')

            st.plotly_chart(fig)


    render_preference_charts(dfu)



with st.container(border=True):
    toc.header("5. Highlights")
    st.markdown("""
                
    *Higher volume of transacted amount was initially driven by increase of monthly registrations on 'micro' segment, and later on, by increase of customer profitability on the 'SMB' segment*  
    - Considering the all active segments, and the `transacted_amount` metric as starting point, it's noticeable that most cohorts newer than **2024-07** have **transacted more money thans older cohorts, since the very first month of registration**.
    - When looking at `acquiring_merchants` though, we notice a remarkable incresase on the monthly new registrations on that same month, possibly leveraged by the 'micro' segment which had a sudden increase on registrations on that period.
    - However, when analyzing the `avg_transacted_amount` metric, this same turning point is not confirmed, instead, it seems there was a significant uprise on this metric later, by 2024-12, driven by the same movement on the 'SMB' segment.
    - This led us to believe that the observable increase on transacted money was initially boosted by new registrations, and later on, by the increasing profitability of customers   
                
    *The first 3 months since registration are critical to avoid customer churn on acquiring and banking*
    - When considering both `acquiring_merchants` and `banking_merchants` metrics, it's observable for all cohorts that there is a significant decrease of active customers after the 3rd month of registration.
    - It is possible that these customers are still active in another products, though, but it remains as warning sign to work on customer retention on these products.
    - This seems to be a common pattern emerging from 'micro' segment.

    *Smartcash is a mature proven product, with room for growth*
    - It's undeniable that smartcash has earned his place among InfinitePay most popular products.
    - Over time, it has earned its share among customer spenses on most segments, particularly SMB and card_not_present, and mantained a considerable share on others too (micro and even inactive)
    - Besides, from the cohorts we notice, all smartcash metrics point out that the "older" the customer registration gets, more likely he is to adhere to some of the credit/loan products. A trend which is particularly sgnificant for Smartcash.

    *InfiniteCard on decline?*
    - Over time, this product had its comings and goings, varying both on number of merchants and amount spent, also presenting lower average ticket than most products.
    - Furthermore, it lost his preference in exchange for other products like smartcash and pix credit
    - Maybe it is not anymore a product worthwhile keeping on InfinitePay product portfolio. Maybe it would be beneficial to focus on other products with higher potential.   

    *Acquiring is a milk-cow*
    - Acquiring has grown both on number of merchants, amount spent and average ticket.  
    - However, the 3-month churn previously mentioned is concerning.
    - Mayber acquiring works best as an onboarding product, and during this 3-month period, InfinitePay should focus on cross-seling some of the growing products like smartcash and pix credit, as a retention strategy.

    *Pix Credit is a rising star and a candidate product to churn prevention*
    - Although the first customers started using Pix Credit by 2024-06, this product only started to really take off by 2024-12. 
    - Pix Credit has stepped up the rankings for all segments since its launch, also from the cohorts, all Pix Credit metrics point out that this product adoption has grown a lot on all segments since its laucn
    - However, it seems to have stabilized on the last 3 months. Maybe it's a good time to boost adoption again with Marketing campaigns.
    - This product is particularly popular among inactive customers from all cohorts (along with smartcash). 
    - Such behaviour possibly suggests that although a customer might be considered "inactive", he didn't stray away from the company's reach and still keeps a relatioship with it.
    - Also suggests that Pix Credit might be a good candidate product for a possible customer retention effort.
                
    """)



toc.generate()