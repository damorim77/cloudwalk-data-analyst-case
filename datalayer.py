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
            aux = pd.read_pickle("data_unpivoted.gz")
        except:

            aux: pd.DataFrame = self.df.copy()
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
                aux[ f"avg_{money_col}" ] = aux[money_col] / aux[qty_col]

            aux['months_since_register'] = (aux['date'] - aux['cohort']).dt.days // 30

            aux['cohort'] = aux['cohort'].dt.strftime('%Y-%m')
            aux['date'] = aux['date'].dt.strftime('%Y-%m')

            aux_money: pd.DataFrame = aux.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'money') & (meta['meta_active'] == True) & (meta['meta_calculation'] == False) ]['column']
            ).copy()

            aux_qty = aux.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'unit') ]['column']
            ).copy()

            aux_avg = aux.melt(
                id_vars = id_vars ,
                var_name = 'metric' ,
                value_vars = meta[ (meta['meta_kind'] == 'money') & (meta['meta_active'] == True) & (meta['meta_calculation'] == True) ]['column']
            ).copy()

            aux_money['product'] = aux_money['metric'].apply(get_product)
            aux_qty['product'] = aux_qty['metric'].apply(get_product)
            aux_avg['product'] = aux_avg['metric'].apply(get_product)

            id_vars += ['product']


            aux = aux_money.merge(aux_qty, on=id_vars).merge(aux_avg, on=id_vars)
            aux = aux.rename(columns=columns_to_rename)
            aux = aux[  id_vars + list(columns_to_rename.values())]
            aux = aux.fillna(0)

            aux.to_pickle("data_unpivoted.gz")

        if tweak_values_for_animation:
            for c in columns_to_rename.values():
                aux[c] = aux[c].apply(lambda v: v if v > 0 else 0.1)

        return aux

    def load_with_share(self):

        dfu = self.load_unpivoted(tweak_values_for_animation=False)

        import sqlite3

        with sqlite3.connect(":memory:") as conn:

            dfu.to_sql('data', conn, index=False)

            dfg = pd.read_sql_query(""" 
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
                        where segment <> 'inactive'
                        group by
                            date,
                            product                                       
                    ) x                                    
                ) y
            """,conn)

        return dfg