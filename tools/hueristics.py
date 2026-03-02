from datetime import datetime

def detect_dormancy(txs, gap_days = 180):
  if len(txs) < 2:
        return False
  for i in range(len(txs)-1):
      dt = datetime.strptime(txs[i]["timeStamp"], "%Y-%m-%d %H:%M:%S")
      dt_2 = datetime.strptime(txs[i+1]["timeStamp"], "%Y-%m-%d %H:%M:%S")
      gap = dt_2 - dt
      if gap.days > gap_days:
       return True
  return False

def detect_fan_out(txs, address, threshold = 10):
   daily_recepts = {}
   for i in range(len(txs)):
      if(txs[i]["from"].lower() == address.lower()):
        date = txs[i]["timeStamp"][:10]
        if date not in daily_recepts:
           daily_recepts[date] = set()
        daily_recepts[date].add(txs[i]["to"])
   for date, recipients in daily_recepts.items():
     if len(recipients) > threshold:
        return True
   return False 

def detect_rapid_passthrough(txs, address, window_seconds=300):
   for i in range(len(txs)):
      if(txs[i]["to"].lower() == address.lower()):
         for j in range(len(txs)):
            if(txs[j]["from"].lower() == address.lower()):
               t1 = datetime.strptime(txs[i]["timeStamp"], "%Y-%m-%d %H:%M:%S").timestamp()
               t2 = datetime.strptime(txs[j]["timeStamp"], "%Y-%m-%d %H:%M:%S").timestamp()
               diff = abs(t2 - t1)
               if diff < window_seconds:
                  return True
   return False

def detect_peel_chain(txs, address, min_ratio=0.8):
  for i in range(len(txs)):
      if(txs[i]["to"].lower() == address.lower()):
         value_1 = txs[i]["value"]
         for j in range(len(txs)):
            if(txs[j]["from"].lower() == address.lower()):
              value_2 = txs[j]["value"]
              if value_1 > 0 and value_2 / value_1 >= min_ratio:
                 return True
  return False
                
   

'''if __name__ == "__main__":
    from etherscan import get_transactions, parse_transactions
    
    raw = get_transactions("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    txs = parse_transactions(raw)
    print("dormancy:", detect_dormancy(txs))
    print("fan_out:", detect_fan_out(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))
    print("rapid_passthrough:", detect_rapid_passthrough(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))
    print("peel_chain:", detect_peel_chain(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))'''
