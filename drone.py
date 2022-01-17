# network control of alcove.py
# interfaces with redis-client to execute commands from queen

import alcove

def main():
    listCom()
    key = '1'
    alcove.callCom(key)

def listCom():
    keys = alcove.com.keys()
    print(50*"=")
    print("commands available:")
    for key in keys:
        print(key)
    print(50*"=")

if __name__ == "__main__":
    main()