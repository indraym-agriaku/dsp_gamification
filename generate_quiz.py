import os
import sys
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
import itertools
import joblib
import random
import json
import argparse
import random_batch as rb


from credential_accessor import CredentialAccessor 
from dao.google_bigquery import GoogleBigQuery as gbq 

PATH_QUERY  = os.path.join(os.getcwd(),'queries')
PATH_OUTPUT_RANDOM = os.path.join(os.getcwd(),'random_prd_arr_id')


if __name__ == "__main__" :
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--cluster',dest='cluster',metavar='',type=str,required = True,help = "Cluster in which the quiz will be conducted")
    parser.add_argument('--env',dest='env',metavar='',type=str,required = False,help = 'Environment in which the quiz information will be stored',default='prod',choices=['prod','dev'])
    parser.add_argument('--date',dest='date',metavar='',type=str,required = True,help='Starting date of the quiz')
    parser.add_argument('--on_server',dest='on_server',action='store_true')
    parser.add_argument('--min_prd',dest='min_prd',metavar='',type=int,required = False,help='Minimum number of products in each batch',default=12)
    parser.add_argument('--max_prd',dest='max_prd',metavar='',type=int,required = False,help='Maximum number of products in each batch',default=42)
    args = parser.parse_args()
    dict_args = vars(args)
    print(dict_args)
    ## Initiate GBQ Client
    
    print(f"> Initiate the GBQ Client for {dict_args['env']}")
    creds_accessor = CredentialAccessor(env = dict_args['env'], on_server= False)
    myGBQ = gbq(attr = creds_accessor.get_attr())
    ###########################################################################################################################
    # DATA EXTRACTION
    ## Get pareto for cluster 
    eval_date = datetime.strptime(dict_args['date'],"%Y%m%d")
    month_pareto = datetime.strptime(dict_args['date'],"%Y%m%d").strftime("%m/01/%Y")
    with open(os.path.join(PATH_QUERY,'list_pareto.sql'),'r') as f:
        pareto_df  = myGBQ.gbq_read(f.read().format(pareto_date=month_pareto,cluster_name = dict_args['cluster']))
    pareto_df = pareto_df.sample(frac=1).reset_index(drop=True) #Shuffle the pareto list
    
    print(f"> Found {pareto_df.shape[0]} pareto products in cluster {dict_args['cluster']} and pareto month : {month_pareto}")
    
    if pareto_df.empty : 
        print(f"> Execution ends")
        
    else :
        ## Get non pareto for cluster 
        now_date = datetime.now()
        END_TRX_PERIOD = eval_date.strftime(f"%Y-%m-01")
        START_TRX_PERIOD = (eval_date+relativedelta(months=-1)).strftime(f"%Y-%m-01")
        with open(os.path.join(PATH_QUERY,'list_non_pareto.sql'),'r') as f:
            non_pareto_df  = myGBQ.gbq_read(f.read().format(cluster_name = dict_args['cluster'],
                                                       pareto_date = month_pareto,
                                                       START_TRX_PERIOD = START_TRX_PERIOD,
                                                       END_TRX_PERIOD = END_TRX_PERIOD,
                                                       N_prd = pareto_df.shape[0]))
        non_pareto_df = non_pareto_df.sample(frac=1).reset_index(drop=True) #Shuffle the non pareto list
        print(f"> Found {non_pareto_df.shape[0]} non-pareto products in cluster {dict_args['cluster']} with period trx ({START_TRX_PERIOD} - {END_TRX_PERIOD}) and pareto month : {month_pareto}")
        
        # Create the list for all products 
        pareto_df['is_assortment'] = True 
        non_pareto_df['is_assortment'] = False 
        list_prd_df  = pd.concat([pareto_df[['prd_id','is_assortment']],non_pareto_df[['prd_id','is_assortment']]],axis = 0)
        list_prd_df['cluster'] = dict_args['cluster'].upper()
        list_prd_df = list_prd_df.reset_index(drop=True)

        ###########################################################################################################################
        # DATA PROCESSING

        ## Searching best number of batches 
        searching_cond = False 
        max_divider = dict_args['max_prd']
        if max_divider%2 == 1 : 
            max_divider = max_divider - 1
        else : 
            pass
        multiplier = max_divider / 2 
        
        while not searching_cond :
            divider = multiplier*2
            if ((pareto_df.shape[0]+non_pareto_df.shape[0])%divider > 0) and ((pareto_df.shape[0]+non_pareto_df.shape[0])%divider < dict_args['min_prd']) :
                multiplier = multiplier-1
            else : 
                searching_cond = True

        num_of_batch = int(np.floor((pareto_df.shape[0]+non_pareto_df.shape[0])/divider))
        remainder = (pareto_df.shape[0]+non_pareto_df.shape[0])%divider
        best_num_of_batch = num_of_batch+1 if remainder > 0 else num_of_batch 
        print(f"> Config : {num_of_batch}*{int(divider)}\n Remainder : {int((pareto_df.shape[0]+non_pareto_df.shape[0])%divider)}\n Total Batch : {best_num_of_batch}")

        
        ## Split products into batches 
        random_state = np.random.RandomState(42)
        total_prd = int(pareto_df.shape[0]+non_pareto_df.shape[0])
        pareto_prd_arr = random_state.permutation(np.array(pareto_df.prd_id.to_list()))
        nonpareto_prd_arr = random_state.permutation(np.array(non_pareto_df.prd_id.to_list()))
        total_prd_arr = np.array(pareto_prd_arr.tolist()+nonpareto_prd_arr.tolist())
        print(f"> Do permutation on both the pareto and nonpareto prd list")

        ## Split pareto
        max_item_pareto_group = int(np.floor(divider/2))
        prd_group_pareto_list = rb.split_array(pareto_prd_arr,set_max = max_item_pareto_group)
        print(f"> Success on splitting the list of pareto prd with shape {len(prd_group_pareto_list)}")

        ## Split non pareto
        max_item_nonpareto_group = int(divider-np.floor(divider/2))
        prd_group_nonpareto_list = rb.split_array(nonpareto_prd_arr,set_max = max_item_nonpareto_group)
        print(f"> Success on splitting the list of nonpareto prd with shape {len(prd_group_pareto_list)}")

        ## Get all 
        prd_group_list = []
        len_prd_group_list_member = []
        for i,j in zip(prd_group_pareto_list,prd_group_nonpareto_list):
            prd_group_list.append(np.array(i.tolist()+j.tolist()))
            len_prd_group_list_member.append(np.array(i.tolist()+j.tolist()).shape[0])
        print(f"> Checking...\n Number of prd group : {len(prd_group_list)}\n Num of Element of each group : {set(len_prd_group_list_member)}")

        prd_group_dict = dict([(f"{dict_args['cluster'].upper()}_{eval_date.strftime('%Y%m01')}_{str(i+1).zfill(2)}",list_) for i,list_ in enumerate(prd_group_list)])
        prd_group_df = pd.DataFrame({'prd_group_id':prd_group_dict.keys(),'cluster':[f"{dict_args['cluster'].upper()}"]*(len(prd_group_dict.keys()))})
        prd_group_df['list_prd_id'] = prd_group_df['prd_group_id'].apply(lambda x : json.dumps({f"prd_ids":prd_group_dict[x].tolist()}))
        pareto_snapshot = datetime.strptime(eval_date.strftime("%Y-%m-01"),"%Y-%m-%d")
        
        # Creating snapshot and prc_dt for prd_group_df
        prd_group_df['pareto_snapshot_dt'] = pareto_snapshot
        prd_group_df['prc_dt'] = datetime.now()
        
        # Creating snapshot and prc_dt for list_prd_df 
        list_prd_df['pareto_snapshot_dt'] = pareto_snapshot
        list_prd_df['prc_dt'] = datetime.now()
        
        
        if prd_group_df.duplicated(subset=['list_prd_id']).sum() > 0 :
            raise Exception(f"There are {prd_group_df.duplicated(subset=['list_prd_id']).sum()} groups")
        else :
            print(f"> Success on creating {prd_group_df.shape[0]} prd groups")

        ## Create quizzes 
        prd_group_quiz_dict = {}
        quiz_list = []
        for prd_group in prd_group_dict.keys():
            pool_prd = prd_group_dict[prd_group]
            print(prd_group,pool_prd.shape[0])
            idx_arr,bincount_idx = rb.create_random_set(
                n_prd = pool_prd.shape[0],
                min_appear = 2,
                set_size = 3
            )
            quiz_arr = pool_prd[idx_arr]
            prd_group_quiz_dict[prd_group.upper()] = quiz_arr 
            for i in range(quiz_arr.shape[0]):
                quiz_id = f"{prd_group}_{str(i+1).zfill(2)}"
                prd_group_id = prd_group
                sequence = i+1
                list_prd = json.dumps({f"prd_ids":quiz_arr[i].tolist()})
                quiz_list.append((quiz_id,prd_group_id,dict_args['cluster'].upper(),sequence,list_prd))
        prd_group_df['quiz_array'] = prd_group_df['prd_group_id'].apply(lambda x : json.dumps({f"quiz_array":prd_group_quiz_dict[x].tolist()}))
        prd_quiz_df = pd.DataFrame(data = quiz_list,columns=['quiz_id','prd_group_id','cluster','sequence','list_prd_id'])
        prd_quiz_df['pareto_snapshot_dt'] = pareto_snapshot
        prd_quiz_df['prc_dt'] = datetime.now()
        if prd_quiz_df.duplicated(subset=['list_prd_id']).sum() > 0 :
            raise Exception(f"There are {prd_quiz_df.duplicated(subset=['list_prd_id']).sum()} quiz")
        else :
            print(f"> Success on composing list of quiz for each prd group\n")



        ## Divide mitra into group 
        with open(os.path.join(PATH_QUERY,'select_mitra_cluster.sql'),'r') as f:
            mitra_df  = myGBQ.gbq_read(f.read().format(cluster_name = dict_args['cluster'].upper(),snapshot_dt = eval_date.strftime("%Y-%m-01")))
        mitra_df = mitra_df.sample(frac=1).reset_index(drop=True)
        print(f"> Found {mitra_df.shape[0]} mitra in cluster {dict_args['cluster']} with maximum created_at = {eval_date.strftime('%Y-%m-01')}")

        mitra_group= rb.split_array(random_state.permutation(mitra_df.mitra_id),n_groups=best_num_of_batch)
        for idx, mitra_id in enumerate(mitra_group):
            if idx==0:
                mitra_group_df = pd.DataFrame({'mitra_id':mitra_id,
                                               'cluster':[f"{dict_args['cluster'].upper()}"]*mitra_id.shape[0],
                                               'mitra_group_id':[f"MITRA_{dict_args['cluster'].upper()}_{eval_date.strftime('%Y%m01')}_{str(idx+1).zfill(2)}"]*mitra_id.shape[0]})
            else : 
                mitra_group_df_temp = pd.DataFrame({'mitra_id':mitra_id,
                                               'cluster':[f"{dict_args['cluster'].upper()}"]*mitra_id.shape[0],
                                               'mitra_group_id':[f"MITRA_{dict_args['cluster'].upper()}_{eval_date.strftime('%Y%m01')}_{str(idx+1).zfill(2)}"]*mitra_id.shape[0]})
                mitra_group_df = pd.concat([mitra_group_df,mitra_group_df_temp],axis=0,ignore_index=True)

        mitra_group_df['pareto_snapshot_dt'] = pareto_snapshot
        mitra_group_df['prc_dt'] = datetime.now()


        ## Create schedule
        arr_prd_group_id = np.sort(prd_group_df.prd_group_id.unique())
        arr_mitra_group_id = np.sort(mitra_group_df.mitra_group_id.unique())
        schedule_index = rb.random_diagonal(n_row = arr_prd_group_id.shape[0])
        schedule = arr_prd_group_id[schedule_index]
        start_date = datetime.strptime(dict_args['date'],'%Y%m%d')
        list_schedule = []
        for i in range(schedule_index.shape[1]) : #loop according batch sequence
            current_batch_date = start_date + relativedelta(weeks=+i)
            end_batch_date = current_batch_date+relativedelta(weeks=1)
            batch_sequence = i+1
            for j in range(schedule_index.shape[0]) : #loop according mitra_group level
                mitra_group = arr_mitra_group_id[j]
                prd_group = schedule[j,i]
                quiz_pool = np.sort(prd_quiz_df[prd_quiz_df['prd_group_id']==prd_group]['quiz_id'].unique())
                quiz_chunck = rb.split_array(quiz_pool,n_groups=7)
                daily_start_date = current_batch_date
                for day_,quiz_group in enumerate(quiz_chunck): #loop the quiz groups for each prd_group
                    current_quiz_date = daily_start_date + relativedelta(days=+day_)
                    day_sequence = day_+1
                    for quiz_items in quiz_group : #loop the single quiz
                        list_schedule.append((mitra_group,dict_args['cluster'].upper(),batch_sequence,prd_group,current_batch_date,end_batch_date,day_sequence,quiz_items,current_quiz_date,end_batch_date))
        columns_mitra_quiz = ['mitra_group_id','cluster','batch_sequence','prd_group_id','batch_start_date','batch_end_date','day_sequence','quiz_id','quiz_start_date','quiz_end_date']
        mitra_group_quiz_df = pd.DataFrame(data=list_schedule,columns = columns_mitra_quiz)
        mitra_group_quiz_df['unique_key'] = mitra_group_quiz_df.mitra_group_id + "_" + mitra_group_quiz_df.quiz_id
        
        ## Add hours to datetime cols 
        # for date_cols in ['batch_start_date','batch_end_date','quiz_start_date','quiz_end_date'] :
        #     mitra_group_quiz_df[date_cols] = pd.to_datetime(mitra_group_quiz_df[date_cols].dt.strftime("%Y-%m-%d %H:%M:%S"),format = "%Y-%m-%d %H:%M:%S")
        
        mitra_group_quiz_df['pareto_snapshot_dt'] = pareto_snapshot
        mitra_group_quiz_df['prc_dt'] = datetime.now()
        print("> Data processing is completed. Begin the uploading process")
        # prd_group_df.to_csv('prd_group.csv',index=False)
        # prd_quiz_df.to_csv('prd_quiz.csv',index=False)
        # mitra_group_df.to_csv('mitra_group.csv',index=False)
        # mitra_group_quiz_df.to_csv('mitra_quiz.csv',index=False)




        ###########################################################################################################################
        ##UPLOAD INTO BIGQUERY TABLE 
        ## CONFIGURE ADDRESS 
        if dict_args['on_server'] :
            pass 
        else : 
            # PRD GROUP
            dict_tables = {}
            dict_tables['PRD_GROUP'] = {
            'target_table' : 'mp_ref.mp_ref_gamification_prd_group_details' ,
            'temp_table' : 'temp.gamification_prd_group_details',
            'partition_key' : 'pareto_snapshot_dt',
            'cluster_keys' : ['cluster'],
            'cols' : ['prd_group_id','cluster','list_prd_id','quiz_array','pareto_snapshot_dt','prc_dt'],
            'cols_types' : ['STRING','STRING','STRING','STRING','DATETIME','DATETIME']}
            
            # PRD GROUP QUIZ 
            
            dict_tables['PRD_GROUP_QUIZ'] = {
            'target_table' : 'mp_ref.mp_ref_gamification_prd_group_quiz_mapping' ,
            'temp_table' : 'temp.gamification_prd_group_quiz_mapping',
            'partition_key' : 'pareto_snapshot_dt',
            'cluster_keys' : ['cluster','prd_group_id'],
            'cols' : ['quiz_id','prd_group_id','cluster','sequence','list_prd_id','pareto_snapshot_dt','prc_dt'],
            'cols_types' : ['STRING','STRING','STRING','INTEGER','STRING','DATETIME','DATETIME']}
            
            
            # MITRA GROUP
            dict_tables['MITRA_GROUP'] = {
            'target_table' : 'mp_ref.mp_ref_gamification_mitra_group_details' ,
            'temp_table' : 'temp.gamification_mitra_group_details',
            'partition_key' : 'pareto_snapshot_dt',
            'cluster_keys' : ['cluster'],
            'cols' : ['mitra_id','mitra_group_id','cluster','pareto_snapshot_dt','prc_dt'],
            'cols_types' :['INTEGER','STRING','STRING','DATETIME','DATETIME']}

            
            # MITRA GROUP QUIZ
            dict_tables['MITRA_GROUP_QUIZ'] = {
            'target_table' : 'mp_ref.mp_ref_gamification_mitra_group_quiz_mapping' ,
            'temp_table' : 'temp.gamification_mitra_group_quiz_mapping',
            'partition_key' : 'pareto_snapshot_dt',
            'cluster_keys' : ['cluster'],
            'cols' : ['unique_key','mitra_group_id','cluster','batch_sequence','prd_group_id','batch_start_date','batch_end_date','day_sequence','quiz_id','quiz_start_date','quiz_end_date','pareto_snapshot_dt','prc_dt'],
            'cols_types' :['STRING','STRING','STRING','INTEGER','STRING','DATETIME','DATETIME','INTEGER','STRING','DATETIME','DATETIME','DATETIME','DATETIME']}
            
            # PRD LIST
            dict_tables['PRD_LIST'] = {
            'target_table' : 'mp_ref.mp_ref_gamification_prd_list' ,
            'temp_table' : 'temp.gamification_prd_list',
            'partition_key' : 'pareto_snapshot_dt',
            'cluster_keys' : ['cluster'],
            'cols' : ['prd_id','is_assortment','cluster','pareto_snapshot_dt','prc_dt'],
            'cols_types' :['INTEGER','BOOLEAN','STRING','DATETIME','DATETIME']
            }
            
        #input dataframe into dict 
        dict_tables['PRD_GROUP']['df'] = prd_group_df
        dict_tables['PRD_GROUP_QUIZ']['df'] = prd_quiz_df
        dict_tables['MITRA_GROUP']['df'] = mitra_group_df
        dict_tables['MITRA_GROUP_QUIZ']['df'] = mitra_group_quiz_df
        dict_tables['PRD_LIST']['df'] = list_prd_df
                
        # For PRD GROUP 
        for table_ in dict_tables.keys():
            df = dict_tables[table_]['df']
            
            if not myGBQ.gbq_check_table(table_name = dict_tables[table_]['target_table']) :
                # NO TABLE FOUND, create new 
                myGBQ.gbq_write(dataframe = df[dict_tables[table_]['cols']],
                           bq_cols = dict_tables[table_]['cols'],
                           bq_types = dict_tables[table_]['cols_types'],
                           bq_dst_table = dict_tables[table_]['target_table'],
                           bq_write_disposition = 'WRITE_EMPTY',
                           bq_clustering_key = dict_tables[table_]['cluster_keys'],
                           bq_partition_key = dict_tables[table_]['partition_key'])
            
            else : 
                # TABLE IS FOUND 
                myGBQ.gbq_write(dataframe = df[dict_tables[table_]['cols']],
                           bq_cols = dict_tables[table_]['cols'],
                           bq_types = dict_tables[table_]['cols_types'],
                           bq_dst_table = dict_tables[table_]['temp_table'],
                           bq_write_disposition = 'WRITE_TRUNCATE',
                           bq_clustering_key = dict_tables[table_]['cluster_keys'],
                           bq_partition_key = dict_tables[table_]['partition_key'])
                
                ## Deleting the target table 
                DELETE_QUERY = """ DELETE {dataset} WHERE DATE(pareto_snapshot_dt) = '{date_id}' AND cluster = '{cluster_}' """
                myGBQ_client = myGBQ.gbq_client()
                delete_job_ = myGBQ_client.query(
                    DELETE_QUERY.format(
                        dataset = dict_tables[table_]['target_table'],
                        date_id = pareto_snapshot.strftime("%Y-%m-%d"),
                        cluster_ = dict_args['cluster'].upper()
                    )
                )
                delete_job_.result()
                print(f"> Num of deleted rows in {dict_tables[table_]['target_table']} where pareto_snapshot_dt = {pareto_snapshot.strftime('%Y-%m-%d')} and cluster = {dict_args['cluster']} is {delete_job_.num_dml_affected_rows}")
                
                ## Updating the target table
                UPDATE_QUERY = """
                INSERT INTO {target} 
                SELECT * 
                FROM {temp}"""
                
                
                update_job_ = myGBQ_client.query(
                    UPDATE_QUERY.format(
                        target = dict_tables[table_]['target_table'],
                        temp = dict_tables[table_]['temp_table']
                    )
                )
                update_job_.result()
                print(f"> Num of updated rows in {dict_tables[table_]['target_table']} where pareto_snapshot_dt = {pareto_snapshot.strftime('%Y-%m-%d')} and cluster = {dict_args['cluster']} is {update_job_.num_dml_affected_rows}")
                
                
            
            
            
            
        
        
    
        
     
                
        

    
    
    
    
    
    
    
    
    
        
        
            
            
    
    
    
    

    