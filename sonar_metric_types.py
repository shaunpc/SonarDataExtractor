import requests

url = "https://next.sonarqube.com/sonarqube/api/metrics/search"

resp = requests.get(url)

if resp.status_code != 200:
    # This means something went wrong.
    raise Exception('GET api/metrics/search {}'.format(resp.status_code))

json = resp.json()
#print(json)

metrics_list = json['metrics']
total = json['total']
list_start = json['p']
list_finish = json['ps']

print(metrics_list)
counter = 0
for i in metrics_list:
    curr_metric = metrics_list[counter]
    print(curr_metric)
    if curr_metric['id'] == '240':
        for i in curr_metric:
            print(i, ' -> ', curr_metric[i])
    counter = counter + 1
print(counter)

#print(total)
#print(list)
#print(ps)
