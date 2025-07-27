import pandas as pd
import sqlite3

class DataLayer:

    def __init__(self):
        self.df = pd.read_pickle('data.gz')
        self.meta = self.load_meta()

    def load_meta(self):
        return pd.read_json( open('meta.json','r'), orient='index' ).reset_index().rename(columns={'index':'column'})
    
    def load_unpivoted(self, tweak_values_for_animation=True):

        columns_to_rename = {'value_x': 'total_amount', 'value_y': 'total_merchants', 'value':'avg_ticket'}

        try:
            dfu = pd.read_pickle("data_unpivoted.gz")
        except:

            dfu: pd.DataFrame = self.df.copy()
            meta = self.meta

            id_vars = list(meta[ meta['meta_class'] =='dimension' ]['column'])
            get_product = lambda metric:  meta[ meta['column'] == metric ]['meta_product'].iloc[0]


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
                dfu[ f"avg_{money_col}" ] = dfu[money_col] / dfu[qty_col]

            dfu['months_since_register'] = (dfu['date'] - dfu['cohort']).dt.days // 30

            dfu['cohort'] = dfu['cohort'].dt.strftime('%Y-%m')
            dfu['date'] = dfu['date'].dt.strftime('%Y-%m')

            aux_money: pd.DataFrame = dfu.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'money') & (meta['meta_active'] == True) & (meta['meta_calculation'] == False) ]['column']
            ).copy()

            aux_qty = dfu.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'unit') ]['column']
            ).copy()

            aux_avg = dfu.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'money') & (meta['meta_active'] == True) & (meta['meta_calculation'] == True) ]['column']
            ).copy()

            aux_money['product'] = aux_money['metric'].apply(get_product)
            aux_qty['product'] = aux_qty['metric'].apply(get_product)
            aux_avg['product'] = aux_avg['metric'].apply(get_product)

            id_vars += ['product']

            dfu = aux_money.merge(aux_qty, on=id_vars).merge(aux_avg, on=id_vars)
            dfu = dfu.rename(columns=columns_to_rename)
            dfu = dfu[  id_vars + list(columns_to_rename.values())]
            dfu = dfu.fillna(0)

            with sqlite3.connect(":memory:") as conn:

                dfu.to_sql('data', conn, index=False)

                dfu = pd.read_sql_query(f"""
                    select
                        date,
                        cohort,
                        segment,
                        months_since_register,
                        product,
                        total_amount ,
                        total_merchants ,
                        avg_ticket                
                    from data
                                        
                    union all
                                        
                    select 
                        date,
                        'ALL' cohort,
                        segment,
                        null months_since_register,
                        product,
                        sum(total_amount) as total_amount,
                        sum(total_merchants) as total_merchants,
                        sum(total_amount)/sum(total_merchants) as avg_ticket
                    from data
                    group by
                        date,
                        segment,
                        product
                """, conn
                )


            dfu.to_pickle("data_unpivoted.gz")

        if tweak_values_for_animation:
            for c in columns_to_rename.values():
                dfu[c] = dfu[c].apply(lambda v: v if v > 0 else 0.1)

        return dfu

    def load_q1(self):

        dfu = self.load_unpivoted(tweak_values_for_animation=False)
       
        with sqlite3.connect(":memory:") as conn:

            dfu.to_sql('data', conn, index=False)

            dfg = pd.read_sql_query(f""" 
                select 
                    segment ,
                    product ,
                    sum(total_amount) as total_amount ,
                    sum(total_merchants) as total_merchants ,
                    sum(total_amount) / sum(total_merchants) as avg_ticket
                from data
                where date in ('2025-02','2025-03','2025-04') and
                cohort !='ALL'
                group by
                    segment ,
                    product
                order by 
                    segment, avg_ticket desc
            """,conn)

        return dfg
    

    def load_q2(self):

        dfu = self.load_unpivoted(tweak_values_for_animation=False)
       
        with sqlite3.connect(":memory:") as conn:

            dfu.to_sql('data', conn, index=False)

            dfg = pd.read_sql_query(f""" 
                select 
                    x.*,
                    row_number() over (partition by product order by average_merchants_monthly desc) as rank
                from (
                    select 
                        product ,
                        segment ,
                        sum(total_merchants) as total_merchants ,
                        sum(total_merchants) / count(distinct date) as average_merchants_monthly
                    from data
                    where date in ('2025-02','2025-03','2025-04')
                    and cohort != 'ALL'
                    group by
                        segment ,
                        product
                    order by 
                        product, average_merchants_monthly desc
                ) x

            """,conn)

        return dfg
    
    def load_with_share(self, segment,cohort):

        dfu = self.load_unpivoted(tweak_values_for_animation=False)
        
        where_cohort = ''
        if cohort != 'ALL':
            where_cohort = f"and cohort = '{cohort}'"


        with sqlite3.connect(":memory:") as conn:

            dfu.to_sql('data', conn, index=False)

            dfg = pd.read_sql_query(f""" 
                select 
                    date,
                    segment,
                    product,
                    percent_avg_ticket ,
                    row_number() over (partition by date, segment order by percent_avg_ticket desc) as rank
                from (
                    select
                        date,
                        segment,
                        product,
                        avg_ticket / sum(avg_ticket) over (partition by date, segment) as percent_avg_ticket
                    from (
                        select 
                            date,
                            segment,
                            product,
                            sum(avg_ticket) avg_ticket
                        from data
                        where 1=1 
                        {where_cohort}
                        group by
                            date,
                            segment,
                            product  
                                    
                        UNION ALL
                        
                        select 
                            date,
                            'ALL' segment,
                            product,
                            sum(avg_ticket) avg_ticket
                        from data
                        where 1=1 
                        {where_cohort}
                        group by
                            date,
                            product                                       
                                    
                        UNION ALL
                        
                        select 
                            date,
                            'ALL_ACTIVE' segment,
                            product,
                            sum(avg_ticket) avg_ticket
                        from data
                        where 1=1 
                            and segment <> 'inactive'
                            {where_cohort} 
                        group by
                            date,
                            product                                       
                    ) x   
                    where segment = '{segment}'                                 
                ) y
            """,conn)

        return dfg