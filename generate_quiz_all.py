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

import subprocess

from credential_accessor import CredentialAccessor 
from dao.google_bigquery import GoogleBigQuery as gbq 

PATH_QUERY  = os.path.join(os.getcwd(),'queries')
PATH_OUTPUT_RANDOM = os.path.join(os.getcwd(),'random_prd_arr_id')
# CLUSTER_LIST = ['Bocimi','Priangan Timur 2','Bandung Raya','Kapursub','Ciayumajakuning','Priangan Timur 1']
CLUSTER_LIST = ['Bocimi','Priangan Timur','Bandung Raya','Kapursub','Ciayumajakuning']


if __name__ == "__main__" :
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--env',dest='env',metavar='',type=str,required = False,help = 'Environment in which the quiz information will be stored',default='prod',choices=['prod','dev'])
    parser.add_argument('--date',dest='date',metavar='',type=str,required = True,help='Starting date of the quiz')
    parser.add_argument('--on_server',dest='on_server',action='store_true')
    parser.add_argument('--min_prd',dest='min_prd',metavar='',type=int,required = False,help='Minimum number of products in each batch',default=7)
    parser.add_argument('--max_prd',dest='max_prd',metavar='',type=int,required = False,help='Maximum number of products in each batch',default=28)
    args = parser.parse_args()
    dict_args = vars(args)
    print(dict_args)

    for cluster_ in CLUSTER_LIST : 
        print(f"> Running cluster : {cluster_}...")
        COMMAND = f"venv_gamification_experiment/bin/python generate_quiz.py -c '{cluster_}' --date '{dict_args['date']}' --env '{dict_args['env']}' "
        try :
            result = subprocess.run(COMMAND,capture_output = True, text = True, check=True,shell=True)
            print(result.stdout)
            
        except subprocess.CalledProcessError as e :
            print(f"Error : {e}")
        print(f"> End computation for  cluster : {cluster_}...")
            
            
        
    ## Initiate GBQ Clie