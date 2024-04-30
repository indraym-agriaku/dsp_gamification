import os, yaml
from google.cloud import storage as st, bigquery as bq
from google.oauth2.service_account import Credentials as Cr

class CredentialAccessor():
    def __init__(
        self, 
        env : str = "dev", 
        on_server : bool = False,
        *args, **kwargs
    ) -> None:
        """ 
            Usage:
            To initialize all inheritable variables for Credential() class.
            
            Arguments:
            . env -> working environment options, "dev" (development) or "prod" (production)
            . on_server -> whether the access is in local or AWS server
            
            Info:
            . Last edited by: NICHOLAS DOMINIC <nicholas.dominic@agriaku.com>
            . Last edited at: January 13th, 2023
            . Copyright: DATA SCIENCE team, PT. Agriaku Digital Indonesia
        """
        
        super(CredentialAccessor, self).__init__()
        
        # get PROJECT_ROOT_DIR from config.yaml file
        with open("config.yaml", "r") as stream:
            try:
                self.ROOT_DIR = yaml.safe_load(stream)["PROJECT_ROOT_DIR"]
            except yaml.YAMLError as exc:
                print(exc)
        
        # working environment
        self.env = env
        self.on_server = on_server
        self.credentials_local_path = self.ROOT_DIR  + "/credentials"

        # location and project_id in BQ
        self.job_location = "asia-southeast2" # Jakarta area
        self.project_id_dev = "agriaku-dwh-dev-353603" # GCP Project ID - Development
        self.project_id_prod = "disco-song-343611" # GCP Project ID - Production
        
        if self.on_server:
            # keys for server (both dev and prod)
            try:
                self.parent_dir = "/home/ubuntu/agriaku_dwh" # from Variable.get("AGRIAKU_HOME")
                self.cred_path = self.parent_dir + "/keys/sa-gcp-agriaku.json"
            except Exception as e:
                print("[ERROR] {}".format(e))
        else:
            # keys for local
            self.cred_path = self.credentials_local_path + "/dev/"                 if self.env.upper() == "DEV" else self.credentials_local_path + "/prod/"
            self.cred_path += [c for c in os.listdir(self.cred_path) if c.endswith(".json")][0]
        
        # google oauth2 to read credential from JSON-formatted Service Account (sa) file
        self.google_auth_sa_credentials = Cr.from_service_account_file(filename=self.cred_path)
        
    def get_attr(
        self, 
        *args, **kwargs
    ) -> dict:
        """ 
            Usage:
            To get attributes from the class.
            
            Arguments:
            . None
        """
        
        return {
            "on_server" : self.on_server,
            "env" : self.env,
            "loc" : self.job_location,
            "project_id" : self.project_id_dev if self.env.upper() == "DEV" else self.project_id_prod,
            "cred_path" : self.cred_path,
            "cred_sa" : self.google_auth_sa_credentials
        }
    
    def get_gbq_client(
        self,
        *args, **kwargs
    ) -> bq.client.Client:
        """ 
            Usage:
            To get a Google BigQuery client.
            
            Arguments:
            . None
        """
        
        attr = self.get_attr()
        return bq.Client(
            project=attr["project_id"],
            credentials=self.google_auth_sa_credentials
        )
    
    def get_gcs_client(
        self,
        *args, **kwargs
    ) -> st.client.Client:
        """ 
            Usage:
            To get a Google Cloud Storage client.
            
            Arguments:
            . None
        """
        
        attr = self.get_attr()
        return st.Client(
            project=attr["project_id"],
            credentials=self.google_auth_sa_credentials
        )
