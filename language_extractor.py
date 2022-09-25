component = 'module1'
languages = 'java=1234;c=12;xml=344;other=66'

x = languages.split(';')
print(x)
for y in x:
    z = y.split('=')
    lan = z[0]
    cnt = z[1]
    print(component, lan, cnt)

