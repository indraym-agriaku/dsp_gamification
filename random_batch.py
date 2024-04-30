import os
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
import itertools
import joblib
import random

def shift_right_list(list_):
    return [list_[-1]] + list_[:-1]

def create_random_(arr, random_generator, min_appear=3,set_size=3, *args, **kwargs):
    r_ =random_generator
    # Oversampling the list
    len_arr = len(arr)
    arr_sample = np.array(list(arr)*min_appear)
    len_arr_sample = len(arr_sample)
    mod_resid = len_arr_sample%set_size
    
    # Random sorting the list
    if mod_resid == 0:
        arr_sample = list(r_.permutation(arr_sample))
    else : 
        arr_sample = list(r_.permutation(np.concatenate([arr_sample,r_.choice(arr,size=set_size-mod_resid,replace=False)])))
    print(f"Unordered pool :{arr_sample}")
    arranged_sample = np.zeros([int(len(arr_sample)/set_size),set_size])
    
    #Sort the list so that no set has two or more identical items.
    max_trials = 10 #Maximum trials for shifting 
    
    for i in range(arranged_sample.shape[0]):
        print(f"Creating product batch {i+1} ...")
        observed_list = arr_sample[set_size*i:(set_size*(i+1))] #create the chunk
        print(f"Unordered product batch {i+1} : {observed_list}")
        
        if i < arranged_sample.shape[0]-1 :
            for j in range(len(observed_list)):
                if len(observed_list[:j+1])==len(set(observed_list[:j+1])) : #No two or more identical items
                    print(f"Ordering product batch {i+1} : {observed_list[:j+1]}")
                else : # Identical items are found, shifting pool and the chunk
                    print(f"{observed_list[j]} already existed, replace this item by shifting the pool!")
                    trials = 0
                    while trials <= max_trials :
                        trials = trials + 1
                        print(f'Conducting trial {trials}...')
                        arr_sample = arr_sample[:(set_size*i+j)] + shift_right_list(arr_sample[(set_size*i+j):]) #Last element of the pool become the very first element in the observation
                        print(f"Pool has been ordered : {arr_sample}")
                        observed_list[j:] = arr_sample[(set_size*i+j):(set_size*(i+1))]
                        
                        if len(observed_list[:j+1])==len(set(observed_list[:j+1])) : 
                            print(f"Ordering product batch {i+1} : {observed_list[:j+1]}")
                            break 
                        else  : 
                            pass
        else : 
            print(f"Creating last product batch...")
            # Check if the sorting is possible 
            observed_list_arr = np.array(observed_list)
            bincount_last_batch = np.bincount(observed_list_arr)
            problematic_items = np.where(bincount_last_batch == 2)[0]
            for items_ in problematic_items:
                print(f"{items_} is found having duplicate, fixing this issue...") #Do resampling if an issue is found
                location_items = np.where(observed_list_arr == items_)[0]
                observed_list_arr[location_items[0]] = r_.choice(arr[~np.isin(arr,np.array(list(set(observed_list_arr))))])
                print(f"Ordering product batch {i+1} : {observed_list_arr}")
            print(f"Ordering product batch {i+1} : {observed_list_arr}")
            observed_list = list(observed_list_arr)
            arr_sample[set_size*i:(set_size*(i+1))] = observed_list
                
                
            
        arranged_sample[i,:] = np.array(observed_list)
                    
    return arranged_sample.astype(int), np.bincount(np.array(arr_sample))

def check_row_similarity(arr_ : np.array, *args, **kwargs) :
    n_row = arr_.shape[0]
    pool_ = np.arange(n_row)
    val_ = False
    for i in itertools.combinations(pool_,2):
        if set(arr_[i[0],:]) == set(arr_[i[1],:]):
            val_ = True 
            break
    return val_

def checking_bincount_less(arr_ : np.array,min_appear = 3,*args,**kwargs):
    idx_contrary = np.where(arr_ < min_appear)
    return any(idx_contrary[0])

def create_random_set(n_prd : int , min_appear : int = 3, set_size : int = 3, *args, **kwargs):
    PATH_OUTPUT = os.path.join(os.getcwd(),'outputs','random_prd_arr_id')
    namefile = f"n{n_prd}_appear{min_appear}_setsize{set_size}.pickle"
    r_ = np.random.RandomState(12345)
    if os.path.exists(os.path.join(PATH_OUTPUT,namefile)):
        print(f"Product array for this arrangement was already done at : {os.path.join(PATH_OUTPUT,namefile)}")
        sorted_arr = joblib.load(os.path.join(PATH_OUTPUT,namefile))
        for i in range(sorted_arr.shape[0]) :
            if i==0:
                bin_count_ = sorted_arr[i,:]
            else:
                bin_count_ = np.concatenate([bin_count_,sorted_arr[i,:]])
        return sorted_arr, np.bincount(bin_count_.astype(int))
    
    else :
        print(f"Creating prd batches for this arrangement")
        if not os.path.exists(PATH_OUTPUT) :
            os.mkdir(PATH_OUTPUT)
        else :
            pass
        arr = np.arange(n_prd) #Creating list of products
        
        #Generating batches
        sorted_arr,bincount_arr = create_random_(arr=arr,random_generator=r_,min_appear = min_appear,set_size = set_size)
        
        #Checking validity
        val_try = 0
        while val_try < 50:
            if checking_bincount_less(bincount_arr,min_appear=min_appear) or check_row_similarity(sorted_arr):
                val_try = val_try + 1
                print(f'Validity checking results in False criteria with bincount {bincount_arr}, conducting re-trial {val_try}...')
                sorted_arr,bincount_arr = create_random_(arr=arr,random_generator=r_,min_appear = min_appear,set_size = set_size)
            else :
                print(f'Validity checking results in Correct criteria with bincount {bincount_arr}, stopping re-trial {val_try}...')
                break
        
        joblib.dump(sorted_arr,os.path.join(PATH_OUTPUT,namefile))
        print(f"Saving the result to : {os.path.join(PATH_OUTPUT,namefile)}")
        return sorted_arr,bincount_arr
    
    
def random_diagonal(n_row = 15, *args, **kwargs):
    arr = np.ones([n_row,n_row])*-1
    list_id = list(np.arange(n_row))
    for i in range(n_row):
        arr[:,i] = list_id 
        list_id = shift_right_list(list_id)
    return arr.astype(int)

def split_array(arr : np.array, set_max : bool = None, n_groups : int = None):
    if n_groups is not None :
        if n_groups > arr.shape[0] :
            raise ValueError("The number of groups is more than number of items")
        else :
            return np.array_split(arr,n_groups)
    if set_max is not None :
        if set_max > arr.shape[0] :
            raise ValueError("The number of groups is more than number of items")
        else : 
            n_groups = int(np.ceil(arr.shape[0]/set_max))
            split_index = [int(set_max*i) for i in range(1,n_groups+1)]
            split_index[-1] = arr.shape[0]
            splitted_arr = np.split(arr,split_index)
            delete_last_items_ = splitted_arr.pop()
            return splitted_arr
        
            
                
                
        
            
    