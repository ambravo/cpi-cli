import decimal
import getpass
import json
import pickle
import time
import xml.etree.ElementTree as ET
from os.path import expanduser
from xml.etree.ElementTree import Element, SubElement, tostring

import requests
from clint.textui import puts, colored, indent
from requests.auth import HTTPBasicAuth

import constants


def login(arguments):
    if not arguments:
        puts(colored.blue('Account Region: '), False)
        region = input().lower()
        puts(colored.blue('Account ID: '), False)
        account = input().lower()
        puts(colored.green('User Name: '), False)
        user = input()
        password = getpass.getpass()
    else:
        # TO-DO check parameters
        region = arguments[0]
        account = arguments[1]
        user = arguments[2]
        password = arguments[3]

    host = account + '-tmn.hci.' + region + '.hana.ondemand.com'

    operation_url = 'https://' + host + '/Operations/'
    session_op = requests.Session()
    session_op.headers.update({'X-CSRF-Token': 'fetch'})
    response_op = session_op.head(operation_url, auth=HTTPBasicAuth(user, password))

    odata_url = 'https://' + account + '-tmn.hci.' + region + '.hana.ondemand.com/api/v1/'
    session_odata = requests.Session()
    session_odata.headers.update({'X-CSRF-Token': 'fetch'})
    response_odata = session_odata.head(odata_url, auth=HTTPBasicAuth(user, password))

    file_session = {
        "op_url": operation_url,
        "op_token": response_op.headers['X-CSRF-Token'],
        "op_cookies": response_op.cookies,
        "odata_url": odata_url,
        "odata_token": response_odata.headers['X-CSRF-Token'],
        "odata_cookies": response_odata.cookies
    }
    with open(expanduser('~') + constants.SESSION_FILE, 'wb') as file:
        pickle.dump(file_session, file)


def check_if_logged_in():
    with open(expanduser('~') + constants.SESSION_FILE, 'rb') as file:
        file_session = pickle.load(file)
    return file_session


def reuse_session(path, req=None, type='ODATA', method='POST', query=''):
    file_session = check_if_logged_in()
    session = requests.Session()
    if query:
        path = path + '?' + query

    if type == 'ODATA':
        url = file_session['odata_url'] + path
        session.headers.update({'X-CSRF-Token': file_session['odata_token']})
        session.cookies = file_session['odata_cookies']
    else:
        url = file_session['op_url'] + path
        session.headers.update({'X-CSRF-Token': file_session['op_token']})
        session.cookies = file_session['op_cookies']

    if method == 'POST':
        response = session.post(url, req)
    elif method == 'GET':
        response = session.get(url)
    return response, file_session


def participant_list(arguments):
    req = create_request_payload(
        'com.sap.it.op.srv.commands.dashboard.ParticipantListCommand',
        {'withActiveTenants': 'false'},
        {'onlyHeader': 'false', 'withAdminNodes': 'true', 'withNodes': 'true'}
    )
    response, file_session = reuse_session(constants.PARTICIPANT_LIST, req, type='operation')

    doc = ET.fromstring(response.content.decode(constants.ENCODING))
    acc_details = {
        'id': doc.find('./participantInformation/id').text,
        'name': doc.find('./participantInformation/name').text,
        'type': doc.find('./shipmentType').text,
        'version': doc.find('./operationsVersion').text,
        'nodes': []
    }
    for node in doc.findall('./participantInformation/nodes'):
        det = {
            'name': node.find('./name').text,
            'type': node.find('./nodeType').text,
            'version': node.find('./version').text,
            'state': node.find('./nodeState').text,
            'id': node.find('./id').text
        }
        acc_details['nodes'].append(det)
    file_session['acc_details'] = acc_details

    # Account data

    puts(colored.blue('Account Type:\t') +
         acc_details['type'] +
         colored.blue('\tVersion:\t') +
         acc_details['version'])
    puts(colored.blue('Account ID:\t') +
         acc_details['id'] +
         colored.blue('\tAccount Name:\t') +
         acc_details['name'])
    puts(colored.blue('Nodes:'))

    with indent(2, quote='  |--> '):
        for node in acc_details['nodes']:
            puts(
                colored.red('ID: ') +
                node['id'] +
                colored.green('\tName: ') +
                node['name'] +
                colored.green('\tVersion: ') +
                node['version'] +
                colored.green('\tState: ') +
                node['state'] +
                colored.green('\tType: ') +
                node['type']
            )
    get_integration_content()


def create_request_payload(command, attrs, vars):
    root = Element(command)
    for attr in attrs:
        root.set(attr, attrs[attr])
    for var in vars:
        variable = SubElement(root, var)
        variable.text = vars[var]
    return tostring(root, 'utf-8')


def get_messages():
    response, file_session = reuse_session(constants.MSG_LOGS, type='ODATA', method='GET', query='$format=json')
    doc = json.loads(response.content.decode(constants.ENCODING))
    for e in doc['d']['results']:
        print(line([
            e['Status'],
            format_date(e['LogStart']),
            format_date(e['LogEnd']),
            e['AlternateWebLink'],
            e['IntegrationFlowName'],
        ], '\t'
        )
        )


def get_integration_content():
    response, file_session = reuse_session(constants.INT_CONTENT, type='ODATA', method='GET', query='$format=json')
    doc = json.loads(response.content.decode(constants.ENCODING))
    for e in doc['d']['results']:
        print(line([
            e['Status'],
            e['DeployedBy'],
            e['Type'],
            format_date(e['DeployedOn']),
            e['Id'],
            e['Version'],
        ], '\t'
        )
        )


def get_credentials():
    response, file_session = reuse_session(constants.CREDENTIALS, type='ODATA', method='GET', query='$format=json')
    doc = json.loads(response.content.decode(constants.ENCODING))
    for e in doc['d']['results']:
        print(line([
            e['Status'],
            e['DeployedBy'],
            e['Type'],
            format_date(e['DeployedOn']),
            e['Id'],
            e['Version'],
        ], '\t'
        )
        )


def line(texts, separated_by=''):
    final = ''
    for text in texts:
        final += text + separated_by
    return final


def format_date(json_date):
    dd = decimal.Decimal(''.join(i for i in json_date if i.isdigit()))
    s, ms = divmod(dd, 1000)
    return '%s.%03d' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(s)), ms)
