#!/usr/bin/env python3

import json
import sys
import requests


# This module uses Api Reference from Atlassian Jira
# located at
# https://docs.atlassian.com/software/jira/docs/api/REST/7.12.0


def jira_login(username, password, jira_endpoint='http://jiraft.moscow.alfaintra.net/rest/auth/1/session'):
    data = {
        "username": username,
        "password": password
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(jira_endpoint, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print('Http Error occured')
        print(f"Response is {err.response.content}")
        print(f"HTTP Code is {response.status_code}")

    return response.json()


def get_issues_by_project(project, jira_endpoint='http://jiraft.moscow.alfaintra.net/rest/api/2/',
                          user=None, password=None, startpoint=0, expand='', session=None,
                          fields=['*all'], datefrom=None):
    jira_endpoint += 'search'
    results_cnt = 50

    # jql=project=ABC&maxResults=1000
    if datefrom:
        params = {
            "jql": "project = {0} AND (updated >= {1} OR created >= {1}) ORDER BY due".format(project, datefrom),
            "maxResults": results_cnt,
            "startAt": '{}'.format(int(startpoint)),
            "fields": fields
        }
    else:
        params = {
            "jql": "project = {0} ORDER BY due".format(project),
            "maxResults": results_cnt,
            "startAt": '{}'.format(startpoint),
            "fields": fields
        }

    headers = {
        'Content-Type': 'application/json'
    }

    if session:
        headers['cookie'] = f"{session['session']['name']}={session['session']['value']}"

    try:
        if session:
            response = requests.get(jira_endpoint, params=params, headers=headers)
        else:
            response = requests.get(jira_endpoint, params=params, headers=headers, auth=(user, password))
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'Http Error occured. status code is {response.status_code}')
        print(f"Response is {err.response.content}")

    return response.json()


def get_issues_by_type(type, jira_endpoint='http://jiraft.moscow.alfaintra.net/rest/api/2/',
                       user=None, password=None, startpoint=0, expand='', session=None,
                       fields=['*all'], datefrom=None):
    jira_endpoint += 'search'
    results_cnt = 50

    print('filter value inside', type)

    # jql=project=ABC&maxResults=1000
    if datefrom:
        params = {
            "jql": "issuetype = '{0}' AND (updated >= {1} OR created >= {1}) ORDER BY due".format(type, datefrom),
            "maxResults": results_cnt,
            "startAt": '{}'.format(int(startpoint)),
            "fields": fields
        }
    else:
        params = {
            "jql": "issuetype = '{0}' ORDER BY due".format(type),
            "maxResults": results_cnt,
            "startAt": '{}'.format(int(startpoint)),
            "fields": fields
        }

    headers = {
        'Content-Type': 'application/json',
        'charset': 'utf-8'
    }

    if session:
        headers['cookie'] = f"{session['session']['name']}={session['session']['value']}"

    try:
        if session:
            response = requests.get(jira_endpoint, params=params, headers=headers)
        else:
            response = requests.get(jira_endpoint, params=params, headers=headers, auth=(user, password))
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'Http Error occured. status code is {response.status_code}')
        print(f"Response is {err.response.content}")

    return response.json()


def paging_for_issues(filter_value, filter_criteria='project',
                      jira_endpoint='http://jiraft.moscow.alfaintra.net/rest/api/2/',
                      user=None, password=None, startpoint=0, expand='', session=None,
                      fields=['*all'], datefrom=None):
    """ Use this method if you want PAGINATION in get_issues_by_project() """
    responses_list = []
    print(session)
    print("filter value in paging", filter_value)
    if filter_criteria == 'project':
        response = get_issues_by_project(filter_value, jira_endpoint=jira_endpoint, user=user,
                                         password=password, startpoint=startpoint, expand=expand,
                                         session=session, fields=fields, datefrom=datefrom)
    if filter_criteria == 'type':
        response = get_issues_by_type(filter_value, jira_endpoint=jira_endpoint, user=user,
                                         password=password, startpoint=startpoint, expand=expand,
                                         session=session, fields=fields, datefrom=datefrom)
    # responses = dict(response)
    responses_list.append(response)
    while dict(response)['total'] > (startpoint + dict(response)['maxResults']):
        startpoint += dict(response)['maxResults']
        print(f"====BEGIN====")
        print(f"startpoint {startpoint}")
        print(f"total {dict(response)['total']}")
        print("+=====END=====+")
        if filter_criteria == 'project':
            response = get_issues_by_project(filter_value, jira_endpoint=jira_endpoint, user=user,
                                             password=password, startpoint=startpoint, expand=expand,
                                             session=session, fields=fields, datefrom=datefrom)
        if filter_criteria == 'type':
            response = get_issues_by_type(filter_value, jira_endpoint=jira_endpoint, user=user,
                                             password=password, startpoint=startpoint, expand=expand,
                                             session=session, fields=fields, datefrom=datefrom)
        responses_list.append(response)

    return responses_list


def get_all_projects(jira_endpoint='http://jiraft.moscow.alfaintra.net/rest/api/2/',
                     user=None, password=None, startpoint=0, expand='', session=None):
    jira_endpoint += 'project'

    params = {
        'expand': '{}'.format(expand),
        "maxResults": 50,
        "startAt": '{}'.format(int(startpoint)),
        # "fields": [
        #     # "summary",
        #     # "status",
        #     # "assignee"
        #     "*all"
        # ]
    }

    headers = {
        'Content-Type': 'application/json'
    }

    if session:
        headers['cookie'] = f"{session['session']['name']}={session['session']['value']}"

    try:
        if session:
            response = requests.get(jira_endpoint, params=params, headers=headers)
        else:
            response = requests.get(jira_endpoint, params=params, headers=headers, auth=(user, password))
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'Http Error occured. status code is {response.status_code}')
        print(f"Response is {err.response.content}")

    return response.json()


if __name__ == '__main__':

    if len(sys.argv) == 4:
        user = sys.argv[1]
        password = sys.argv[2]
        jira_endpoint = sys.argv[3]
    elif len(sys.argv) == 3:
        user = sys.argv[1]
        password = sys.argv[2]
    else:
        print("Unkown number of arguments, something gone wrong")
        user = "any"
        password = "any"

    session = jira_login(user, password, jira_endpoint='http://jira.moscow.alfaintra.net/rest/auth/1/session')
    fields = ['project',
              'description',
              'summary',
              'subtasks',
              'status',
              'creator',
              'assignee',
              'duedate',
              'issuetype',
              'comment',
              'created',
              'resolutiondate',
              'updated']

    a = paging_for_issues("19101", 'type',
                          expand='operations,versionedRepresentations,editmeta,changelog,renderedFields',
                          user=user, password=password, fields=fields,
                          jira_endpoint='http://jira.moscow.alfaintra.net/rest/api/2/',
                          )

    # a = paging_for_issues("Datalake",
    #                       expand='operations,versionedRepresentations,editmeta,changelog,renderedFields',
    #                       session=session, jira_endpoint='http://jira.moscow.alfaintra.net/rest/api/2/')

    result = json.dumps(a, indent=4, sort_keys=True)

    print(result)

    # with open('debug.json', 'w') as debug_file:
    #     # print(json.dumps(a, indent=4, sort_keys=True, default=lambda x: x.__dict__), file=debug_file)
    #     print(result, file=debug_file)