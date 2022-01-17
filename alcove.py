# the main board functionality
# derivative of kidPy


def my_func_1():
    print('my_func_1() called') 
    
def my_func_2():
    print('my_func_2() called')

def callCom(key):
    if key in com:
        com[key]()
    else:
        print('Invalid key: '+key)

com = {
    '1':my_func_1, 
    '2':my_func_2
}