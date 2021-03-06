import requests
import csv
import sys
import time
import urllib3
from datetime import datetime

# Disable the InsecureRequestWarning from some servers
urllib3.disable_warnings()

#  Documentation of SONAR API
#  https://docs.sonarqube.org/pages/viewpage.action?pageId=2392180
#  https://codeen-app.euclid-ec.org/sonar/web_api/api/components
#
# Full list of web APIs
# https://next.sonarqube.com/sonarqube/api/webservices/list
# https://next.sonarqube.com/sonarqube/api/components/search?qualifiers=TRK
#
# GET structure
# http://MY_HOST/api/measures/component?metricKeys=ncloc,complexity,violations&component=project_key
#
# Here is a sample project (TRK) to try it on
# https://next.sonarqube.com/sonarqube/dashboard?id=sonarts
#
# Project Summary Metric Data of interest
Reliability = "bugs,reliability_rating"
Security = "vulnerabilities,security_rating"
Maintainability = "code_smells,sqale_rating"
Coverage = "coverage"
Duplications = "duplicated_lines_density"
# Further Portfolio Summary Metric Data of interest
Portfolio = "releasability_rating,security_review_rating"
# Portfolio = "new_technical_debt" << Older versions of sonar don't have releasability/sec-review
Complexity = "complexity,cognitive_complexity,class_complexity,file_complexity,function_complexity"
Admin = "last_commit_date,ncloc,ncloc_language_distribution"

# Define the header row for output file
output_row_list = [["Type", "Name", "Key",
                    "Reliability Rating", "Bugs",
                    "Security Rating", "Vulnerabilities",
                    "Maintainability", "Code Smells",
                    "Coverage",
                    "Duplications",
                    "Releasability Rating", "Security Review Rating",
                    "Complexity", "Cognitive Complexity", "Class Complexity", "File Complexity", "Function Complexity",
                    "Last Commit Date", "NC-LoC", "Languages",
                    "Quality Gate", "Sonar Instance"]]


# show a simple progress bar
def progress(full, now):
    sys.stdout.write('\r')
    sys.stdout.write("%d%%" % (now / full * 100))
    if now == full:
        sys.stdout.write('\n')
    sys.stdout.flush()
    return now + 1


# call the sonar WEB API and return JSON output
def sonar_web_api(url, parameters):
    full = url + parameters
    resp = requests.get(full, verify=False)
    if resp.status_code != 200:
        # This means something went wrong.
        raise Exception('GET ', parameters, ' {}'.format(resp.status_code), ' {}'.format(resp.text))
    try:
        return resp.json()
    except ValueError:
        return resp.text


# metrics can come back in any order - return specific value from the full metrics list
def parse_metric(full_list, my_metric, b_convert_to_date = None):
    for m in full_list:
        if my_metric == m['metric']:
            if b_convert_to_date:
                return datetime.fromtimestamp(float(m['value']) / 1000).strftime('%Y-%m-%d')
            return m['value']
    return 'not found'


# go find details about the specified Sonar repo
def interrogate_sonar_repo(sonar_url):
    interrogate_sonar_repo_projects(sonar_url)
    interrogate_sonar_repo_portfolios(sonar_url)


# get the metrics for the specified component list (used for both projects and portfolios)
def interrogate_sonar_component_metrics(sonar_url, total, components, mode):
    metrics_url_part1 = "api/measures/component?component="
    metrics_url_part2 = "&metricKeys=" + Reliability + "," + Security + "," + \
                        Maintainability + "," + Coverage + "," + Duplications + "," + Portfolio + "," + \
                        Complexity + "," + Admin
    count = 1
    for item in components:
        count = progress(total, count)
        project_id = item['key']
        project_name = item['name']
        # Get the quality gate in-use for this project
        quality_gate_url = "api/qualitygates/get_by_project?project=" + project_id
        quality_gate_json = sonar_web_api(sonar_url, quality_gate_url)
        quality_gate = quality_gate_json['qualityGate']['name']

        # Get the metrics for this project
        metrics_url = metrics_url_part1 + project_id + metrics_url_part2
        # print(metrics_url_full)
        metrics_json = sonar_web_api(sonar_url, metrics_url)
        metrics_component = metrics_json['component']
        metrics_string = metrics_component['measures']
        output_row = [mode, project_name, project_id,
                      parse_metric(metrics_string, 'reliability_rating'),
                      parse_metric(metrics_string, 'bugs'),
                      parse_metric(metrics_string, 'security_rating'),
                      parse_metric(metrics_string, 'vulnerabilities'),
                      parse_metric(metrics_string, 'sqale_rating'),
                      parse_metric(metrics_string, 'code_smells'),
                      parse_metric(metrics_string, 'coverage'),
                      parse_metric(metrics_string, 'duplicated_lines_density'),
                      parse_metric(metrics_string, 'releasability_rating'),
                      parse_metric(metrics_string, 'security_review_rating'),
                      parse_metric(metrics_string, 'complexity'),
                      parse_metric(metrics_string, 'cognitive_complexity'),
                      parse_metric(metrics_string, 'class_complexity'),
                      parse_metric(metrics_string, 'file_complexity'),
                      parse_metric(metrics_string, 'function_complexity'),
                      parse_metric(metrics_string, 'last_commit_date', True),
                      parse_metric(metrics_string, 'ncloc'),
                      parse_metric(metrics_string, 'ncloc_language_distribution'),
                      quality_gate, sonar_url]
        output_row_list.append(output_row)


# pull project components, then metrics for each component from the specified sonar repository
def interrogate_sonar_repo_projects(sonar_url):
    # TRK is Projects, VW is Portfolios)
    version = sonar_web_api(sonar_url, "api/server/version")
    page_size = 500
    page = 1
    print("Starting to obtain projects from {} (Version:{})".format(sonar_url, version))
    while True:
        search_qualifier = "api/components/search?qualifiers=TRK&ps={}&p={}".format(page_size, page)
        projects = sonar_web_api(sonar_url, search_qualifier)
        total = projects['paging']['total']
        if (page * page_size > total):
            remaining_page_size = total - ((page-1)*page_size)
        else:
            remaining_page_size = page_size
        print("Grabbing {} projects as page {}".format(remaining_page_size, page))
        interrogate_sonar_component_metrics(sonar_url, remaining_page_size, projects['components'], "PROJECT")
        if page * page_size > total:
            break
        else:
            page = page + 1
    print("Completed project processing : {}".format(total))


# pull portfolio components, then metrics for each component from the specified sonar repository
def interrogate_sonar_repo_portfolios(sonar_url):
    # TRK is Projects, VW is Portfolios)
    portfolios = sonar_web_api(sonar_url, "api/components/search?qualifiers=VW")
    total = portfolios['paging']['total']
    print("Processing {} portfolios from {}".format(total, sonar_url))
    interrogate_sonar_component_metrics(sonar_url, total, portfolios['components'], "PORTFOLIO")


# Define which Sonar repos we want to scan for projects
interrogate_sonar_repo("https://next.sonarqube.com/sonarqube/")
# interrogate_sonar_repo_projects("https://next.sonarqube.com/sonarqube/")

# Now store it away in a file (with timestamp in name)
filename = 'sonar_ratings_{}.csv'.format(time.strftime("%Y%m%d-%H%M%S"))
with open(filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(output_row_list)

print("Finished: Processed {} results into {}".format(len(output_row_list) - 1, file.name))
