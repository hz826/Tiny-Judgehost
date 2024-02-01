import time

s = input().split()
a = int(s[0])
b = int(s[1])

for i in range(100000000) :
    a += i

for i in range(100000000) :
    a -= i

print(a+b)