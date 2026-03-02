
def load_sanctioned_addresses():
    file_path = 'data/sanctioned_addresses_ETH.txt'
    addresses = set()
    try:
        with open(file_path, 'r') as file:
            for line in file:
             addresses.add(line.strip())
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    return addresses

def is_sanctioned(address, sanctioned_set):
  return address in sanctioned_set

'''if __name__ == "__main__":
    sanctioned = load_sanctioned_addresses()
    
    print(is_sanctioned("0x098B716B8Aaf21512996dC57EB0615e2383E2f96", sanctioned))
    
    print(is_sanctioned("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", sanctioned))'''
   

