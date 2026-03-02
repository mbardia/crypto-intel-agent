import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL =  "https://api.etherscan.io/v2/api"



def get_transactions(address):
  params = {
    "module" : "account",
    "action" : "txlist",
    "address" : address,
    "startblock" : 0,
    "endblock" : 99999999,
    "sort" : "asc",
    "chainid": 1,
    "apikey" : API_KEY
  }
  response = requests.get(BASE_URL, params = params)
  data = response.json()    
  return data["result"]  

def parse_transactions(raw_json):
  parsed  = []
  for tx in raw_json:
    parsed.append({
      "from" : tx["from"],
      "to" : tx["to"],
      "value" :  int(tx["value"])/10**18,
      "timeStamp" : datetime.fromtimestamp(int(tx["timeStamp"])).strftime("%Y-%m-%d %H:%M:%S"),
      "hash" : tx["hash"],
      "functionName" : tx["functionName"],
      "isError" : tx["isError"] 
    })
  return parsed

def get_token_transfers(address):
  params = {
    "module" : "account",
    "action" : "tokentx",
    "address" : address,
    "startblock" : 0,
    "endblock" : 99999999,
    "sort" : "asc",
    "chainid": 1,
    "apikey" : API_KEY
  }
  response = requests.get(BASE_URL, params = params)
  data = response.json()    
  return data["result"]  

def get_internal_transactions(address):
  params = {
    "module" : "account",
    "action" : "txlistinternal",
    "address" : address,
    "startblock" : 0,
    "endblock" : 99999999,
    "sort" : "asc",
    "chainid": 1,
    "apikey" : API_KEY
  }
  response = requests.get(BASE_URL, params = params)
  data = response.json()    
  return data["result"]  


'''if __name__ == "__main__":
    raw = get_transactions("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    txs = parse_transactions(raw)
    #for tx in txs[:5]:  
        #print(tx)
    raw_tokens = get_token_transfers("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    #for tx in raw_tokens[:3]:
        #print(tx)
    raw_internal = get_internal_transactions("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    #for tx in raw_internal[:3]:
      #print(tx)'''





 

