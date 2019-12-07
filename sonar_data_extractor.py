import requests
import csv
import sys
import time

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
Portfolio = "releasability_rating,reliability_rating,security_review_rating"

# Define the header row for output file
output_row_list = [["Type", "Name", "Key",
                    "Reliability Rating", "Bugs",
                    "Security Rating", "Vulnerabilities",
                    "Maintainability", "Code Smells",
                    "Coverage",
                    "Duplications",
                    "Releasability Rating", "Reliability Rating", "Security Review Rating",
                    "Sonar Instance"]]


# show a simple progress bar
def progress(full, now):
    sys.stdout.write('\r')
    sys.stdout.write("%d%% : %s" % ((now / full * 100), '=' * now))
    if now == full:
        sys.stdout.write('\n')
    sys.stdout.flush()
    return now + 1


# call the sonar WEB API and return JSON output
def sonar_web_api(url, parameters):
    full = url + parameters
    resp = requests.get(full)
    if resp.status_code != 200:
        # This means something went wrong.
        raise Exception('GET ', parameters, ' {}'.format(resp.status_code), ' {}'.format(resp.text))
    return resp.json()


# metrics can come back in any order - return specific value from the full metrics list
def parse_metric(full_list, my_metric):
    for m in full_list:
        if my_metric == m['metric']:
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
                        Maintainability + "," + Coverage + "," + Duplications + "," + Portfolio
    count = 1
    for item in components:
        count = progress(total, count)
        project_id = item['key']
        project_name = item['name']
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
                      parse_metric(metrics_string, 'reliability_rating'),
                      parse_metric(metrics_string, 'security_review_rating'),
                      sonar_url]
        output_row_list.append(output_row)


# pull project components, then metrics for each component from the specified sonar repository
def interrogate_sonar_repo_projects(sonar_url):
    # TRK is Projects, VW is Portfolios)
    projects = sonar_web_api(sonar_url, "api/components/search?qualifiers=TRK")
    total = projects['paging']['total']
    print("Processing {} projects from {}".format(total, sonar_url))
    interrogate_sonar_component_metrics(sonar_url, total, projects['components'], "PROJECT")


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
