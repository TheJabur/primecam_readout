# local ui for alcove.py
# envisioned to be primarily for development and maintenance
# when directly working on the drone board

import alcove


def main():

    printCom()
    key = '1'
    alcove.callCom(key)


def printCom():
    '''print available commands (from alcove.py)'''

    print(50*"=")
    print("commands available (command : name):")
    for key in alcove.com.keys():
        print(f"{key} : {alcove.com[key].__name__}")
    print(50*"=")


if __name__ == "__main__":
    main()