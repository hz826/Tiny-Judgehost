import os
import time
from sandbox import sandbox

if __name__ == '__main__' :
    timestamp = lambda : 'J' + time.strftime(r"%Y%m%d_%H%M%S", time.localtime(int(time.time())))
    
    s = sandbox()
    s.create(timestamp(), 'python', 'code/plus-std', 'testcase/plus', silence=True, reset_before_run=True)
    # s.compile()
    result = [s.run('python main.py', '{}'.format(i)) for i in range(1,4)]
    print(result)
    s.remove()

 
    s = sandbox()
    s.create(timestamp(), 'gcc', 'code/plus-cpp-std', 'testcase/plus', silence=True, reset_before_run=True)
    s.compile('g++ main.cpp -o main')
    result = [s.run('./main', '{}'.format(i)) for i in range(1,4)]
    print(result)
    s.remove()


    s = sandbox()
    s.create(timestamp(), 'python', 'code/plus-wa', 'testcase/plus', silence=True, reset_before_run=True)
    # s.compile()
    result = [s.run('python main.py', '{}'.format(i)) for i in range(1,4)]
    print(result)
    s.remove()


    s = sandbox()
    s.create(timestamp(), 'python', 'code/plus-tle', 'testcase/plus', silence=True, reset_before_run=True)
    # s.compile()
    result = [s.run('python main.py', '{}'.format(i), time_limit="4000") for i in range(1,4)]
    print(result)
    s.remove()


    s = sandbox()
    s.create(timestamp(), 'python', 'code/plus-re', 'testcase/plus', silence=True, reset_before_run=True)
    # s.compile()
    result = [s.run('python main.py', '{}'.format(i)) for i in range(1,4)]
    print(result)
    s.remove()