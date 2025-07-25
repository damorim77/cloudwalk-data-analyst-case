import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from toc import Toc

st.set_page_config(layout="wide", page_title='CloudWalk Data Analyst Case')

toc = Toc()

st.title('CloudWalk Data Analyst Case')

df = pd.read_pickle('data.gz')

aux_date_cohort = df[['date','cohort']].copy()

df['cohort'] = df['cohort'].dt.strftime('%Y-%m')
df['date'] = df['date'].dt.strftime('%Y-%m')



st.header("Table of contents")
toc.placeholder()






toc.header("1. Intro")
st.markdown("""
    This app was developed by Danilo Amorim in order to provide visual aid for the CloudWalk Data Analyst case.   
    Below is a sample of the data for the challenge
""")

st.dataframe(df, hide_index=True)






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

    cols = st.columns([1,2])

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
    segment = cols[0].segmented_control(
        "Segment" , 
        ["ALL", "ALL_ACTIVE", "SMB", "micro", "card_not_present","inactive"] ,
        default="ALL",
        selection_mode="single"
    )

    format = {
        'transacted_amount': 'M',
        'account_balance': 'M',
        'account_cashin': 'M',
        'account_cashout': 'M',
        'smartcash_amount_lent': 'M',
        'pix_credit_lent': 'M' ,
        'acquiring_merchants' : 'k' ,
        'banking_merchants': 'k'
    }

    format_factor = {
        'k': {
            'factor': 1_000 ,
            'name': 'thousands'
        } ,
        'M': {
            'factor': 1_000_000 ,
            'name': 'milllions'
        }
    }

    has_format = metric in format.keys()
    metric_title = metric

    if has_format:
        metric_title += f" ({format_factor[format[metric]]['name']})"
        metric_title = metric_title.replace("_"," ").title()

    # Creates a copy of the original dataframe
    aux = df.copy()
    if segment == 'ALL_ACTIVE':
        aux = aux[ aux.segment != 'inactive' ]
    elif segment != 'ALL':
        aux = aux[ aux.segment == segment ]

    # Creates a cross-tabulation of transacted-amount per 'date' and 'cohort' dimensions
    cross_tab = pd.crosstab(
        index=aux['cohort'],
        columns=aux['date'],
        values=aux[metric],
        aggfunc='sum'
    )

    # Creates a hetmap chart
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        cross_tab,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        annot_kws={'size': 8},
        cbar_kws={'label': metric_title  }
    )
    plt.title(f"{metric_title} by cohort and date")
    plt.xlabel('Date')
    plt.ylabel('Cohort')


    if has_format:
        # Format annotations to display in millions
        for text in plt.gca().texts:
            if text.get_text() != 'nan':
                text.set_text('{:.1f}'.format(float(text.get_text()) / format_factor[format[metric]]['factor']  ) + format[metric] )


    cols[1].pyplot(plt)

render_cohort()

st.markdown("""
**Highlights**   
            
*Higher volume of transacted money was initially driven by increase of monthly registrations on 'micro' segment, and later on, by increase of customer profitability on the 'SMB' segment*  
- Considering the all active segments, and the `transacted_amount` metric as starting point, it's noticeable that most cohorts newer than **2024-07** have **transacted more money thans older cohorts, since the very first month of registration**.
- When looking at `acquiring_merchants` though, we notice a remarkable incresase on the monthly new registrations on that same month, possibly leveraged by the 'micro' segment which had a sudden increase on registrations on that period.
- However, when analyzing the `avg_transacted_amount` metric, this same turning point is not confirmed, instead, it seems there was a significant uprise on this metric later, by 2024-12, driven by the same movement on the 'SMB' segment.
- This led us to believe that the observable increase on transacted money was initially boosted by new registrations, and later on, by the increasing profitability of customers   
            
*The first 3 months since registration are vital to avoid customer churn*
- When considering both `acquiring_merchants` and `banking_merchants` metrics, it's observable for all cohorts that there is a significant decrease of active customers after the 3rd month of registration.
- It is possible that these customers are still active in another products, though, but it remains as warning sign to work on customer retention on these products.
- This seems to be a common pattern emerging from 'micro' segment.

*Smartcash has a good fit with long-term customers*
- All smartcash metrics point out that the "older" the customer registration gets, more likely he is to adhere to some of the credit/loan products. A trend which is particularly sgnificant for Smartcash
- This possibly means that smartcash is a product more fittable with mature customers, which has built a solid relationship with InfinitePay
- Furthermore, besides being popular product among active customers, it seems to be a popular product among inactive customers too.

*Pix Credit is a rising star and a customer churn blocker*
- Although the first customers started using Pix Credit by 2024-06, this product only started to really take off by 2024-12. 
- All Pix Credit metrics, for all segments point out that this product is growing on usage every month.
- This product is particularly popular among inactive customers from all cohorts. 
- Such behaviour possibly suggests that although a customer might be considered "inactive", he didn't stray away from the company's reach and still keeps a relatioship with it.
- Also suggests that Pix Credit might be a good candidate offer for a possible customer retention effort.
            
2024-12 was a turning point (for good)
- Many of the products appear to have had a performance boost by this particular month, affecting both banking, pix credit and smartcash products.
- The reason is not yet clear, but surely some factor had a global impact on the products. 
""")



toc.subheader("Product preference analysis")
st.markdown(""" 
Product preference is an inference of which product a customer choose more over other options available.   
This is particularly difficult to measure on financial services because it's often  unclear what it means "to choose more".    
We might consider as a measure of preference:
1. How much money customers allocated on a particular service, but also 
2. How many customers allocated any amount of money on that particular service.  

The problem with the first measure is that it is biased towards customers with higher acquisition power, thus representing the preference of a few, but the second, might not present enough financial relevance for the business.  
In that sense, a more parcimonious measure to encompass both needs is the average ticket per customer.  
By dividing the total amount of money by the number of customers, we get a rough estimate of how much money we might expect a single customer might spend on that product.  
This way, the measure does not overprivilege higher acquisition power customers, nor disregard the financial relevance for the business whatsoever.    
That's the premise adopted for this analysis. In this particular case, the average ticket represents the value we expect a merchant segment to spend on a particular product.
""")

#by segment

# -- time
#by months since registered
#by cohort
#by date 







toc.generate()