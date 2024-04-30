from google.cloud import bigquery as bq
from google.cloud.exceptions import NotFound as NF
from google.oauth2.service_account import Credentials as Cr
from pandas import read_gbq, DataFrame as df
from time import time as t

class GoogleBigQuery():
    def __init__(
        self,
        attr : dict,
        *args, **kwargs
    ) -> None:
        """ 
            Usage:
            For CRUD (Create, Read, Update, Delete) into/from Google BigQuery.
            
            Arguments:
            . attr -> dictionary of attributes, including on_server, env, project_id, etc.
            
            Info:
            . Last edited by: NICHOLAS DOMINIC <nicholas.dominic@agriaku.com>
            . Last edited at: January 27th, 2023
            . Copyright: DATA SCIENCE team, PT. Agriaku Digital Indonesia
        """
        
        super(GoogleBigQuery, self).__init__()
        self.attr = attr
        
    def gbq_client(
        self,
        *args, **kwargs
    ) -> bq.client.Client:
        """ 
            Usage:
            To get a Google BigQuery client.
            
            Arguments:
            . None
        """
        
        return bq.Client(
            project=self.attr["project_id"],
            credentials=self.attr["cred_sa"]
        )
    
    def gbq_check_table(
        self,
        table_name : str,
        *args, **kwargs
    ) -> bool:
        """ 
            Usage:
            ...
            
            Arguments:
            . None
        """
        
        print("Checking table: {} ...".format(table_name))
        
        try:
            r = self.gbq_client().get_table(table=table_name)
            print("[SUCCESS] Table found: {}".format(r))
            return True
        except:
            print("[ERROR] Table not found: {}".format(table_name))
            return False
    
    def gbq_read(
        self,
        query : str,
        *args, **kwargs
    ) -> df:
        """ 
            Usage:
            To read a BigQuery table and return it as a Pandas Dataframe.
            
            Arguments:
            . None
        """
        
        return read_gbq(
            query,
            project_id=self.attr["project_id"], 
            location=self.attr["loc"], 
            credentials=Cr.from_service_account_file(self.attr["cred_path"])
        )
    
    def gbq_write(
        self,
        dataframe : df,
        bq_cols : list,
        bq_types : list,
        bq_dst_table : str,
        bq_write_disposition : str,
        bq_modes : list = None,
        bq_clustering_key : list = None,
        bq_partition_key : str = None,
        bq_partition_type : str = "DAY",
        num_of_retries : int = 3,
        *args, **kwargs
    ) -> None:
        """ 
            Usage:
            To write into a BigQuery table given the Pandas dataframe.
            
            Arguments:
            ...
        """

        if len(bq_cols) != len(bq_types):
            raise ValueError("[ERROR]  should be in the same length with .")
            
        valid_dtypes = ["INTEGER", "FLOAT", "STRING", "DATETIME", "BOOLEAN"]
        bq_types = [t.upper() for t in bq_types]
        if all(item in valid_dtypes for item in bq_types) is False:
            raise ValueError("[ERROR]  should be any of this value: {}".format(valid_dtypes))

        BQ_WRITE_DISP = ["WRITE_APPEND", "WRITE_TRUNCATE", "WRITE_EMPTY"]
        if bq_write_disposition not in BQ_WRITE_DISP:
            raise ValueError("[ERROR]  should be one of these: {}".format(BQ_WRITE_DISP))

        if bq_modes is None:
            bq_modes = ["NULLABLE" for i in bq_cols]

        if bq_partition_key is not None:
            bq_partition_type = bq_partition_type.upper()
            
            BQ_PARTITION_TYPES = ["DAY", "HOUR", "MONTH", "YEAR"]
            if bq_partition_type not in BQ_PARTITION_TYPES:
                raise ValueError("[ERROR]  should be one of these: {}".format(BQ_PARTITION_TYPES))
            
            bq_partition_key = bq.TimePartitioning(type_=bq_partition_type, field=bq_partition_key)

        def sql_type_map(data_type : str, *args, **kwargs) -> dict:
            ENUM_SQL_TYPES = {str(i.name).lower() : i for i in bq.enums.SqlTypeNames}
            return ENUM_SQL_TYPES[data_type]

        start_time = t()
        sc = [bq.SchemaField(name=i, field_type=sql_type_map(j.lower()), mode=k) for i, j, k in zip(bq_cols, bq_types, bq_modes)]
        job = self.gbq_client().load_table_from_dataframe(
            dataframe = dataframe,
            destination = bq_dst_table,
            job_config = bq.LoadJobConfig(
                schema=sc,
                write_disposition=bq_write_disposition,
                time_partitioning=bq_partition_key,
                clustering_fields = bq_clustering_key,
            ),
            num_retries = num_of_retries,
            project = self.attr["project_id"],
            location = self.attr["loc"]
        )
        job.result() # wait for the job to complete

        print("[SUCCESS] Data was successfully inserted to: {} (in {:.2f}s).".format(
            self.attr["project_id"] + "." + bq_dst_table, t()-start_time)
        )
