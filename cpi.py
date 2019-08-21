#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Ariel Bravo Ayala'
__version__ = '0.0.1 Alpha'
__license__ = 'MIT'

import base64
import datetime
import decimal
import json
import os
import pickle
import time
import xml.etree.ElementTree as ElementTree
import zipfile
from datetime import datetime
from os.path import expanduser
from urllib.parse import urlencode
from xml.etree.ElementTree import Element, SubElement, tostring

import click
import requests
# External libraries
from terminaltables import AsciiTable

# Own libraries
import constants
from util.colours import green, red, blue, warning


@click.group()
def cmd_grp_cli(**args):
    return args


@click.command(name='login', help='Log in to your CPI tenant')
@click.option('-u', '--user', help='user name', prompt="User or e-mail", nargs=1)
@click.option('-p', '--password', help='user\'s password', hide_input=True, prompt=True, nargs=1)
@click.option('-h', '--host', help='CPI\'s host', prompt='CPI\'s host', nargs=1)
def cmd_login(user, password, host):
    api_url = 'https://%s/api/v1/' % host
    cmd_url = 'https://%s/Operations/' % host
    show_copyright()
    set_session(user, password, api_url, cmd_url)
    get_node_list(display=True)


@click.command(name='logout', help='Remove you session data')
def cmd_logout():
    remove_current_session()


@click.command(name
               ='nodes', help='List nodes')
def cmd_nodes():
    get_node_list(display=True)


@click.group(name='list', help='List of objects (Integration, Messages, etc)')
def cmd_grp_list(**args):
    return args


@click.command(name='messages', help='List messages')
@click.option('-top', help='Top [x] messages', type=int, nargs=1)
@click.option('-s', '--success', help='Get successful messages', is_flag=True)
@click.option('-e', '--errors', help='Get error messages', is_flag=True)
@click.option('-f', '--from', help='From', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']))
@click.option('-t', '--to', help='To', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']))
def cmd_messages(**args):
    get_messages(args)


@click.command(name='content',
               help='List integration content\n\n By default iflows, odata and valuemapping artifacts will be gathered')
@click.option('-i', '--iflows', help='Include iFlows', is_flag=True)
@click.option('-o', '--odata', help='Include Odata services', is_flag=True)
@click.option('-v', '--value-mapping', help='Include Value Mappings', is_flag=True)
@click.option('-f', '--from', help='From', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']))
@click.option('-t', '--to', help='To', type=click.DateTime(formats=['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']))
def cmd_content(**args):
    get_integration_content(args)


@click.command(name='download', help='Download an integration artefact')
@click.option('--symbolic-name', '-id', help='Artefact\'s ID (Symbolic Name)', type=str, nargs=1, prompt=True)
def cmd_download_artefact(symbolic_name):
    download_iflow(symbolic_name)


cmd_grp_cli.add_command(cmd_login)
cmd_grp_cli.add_command(cmd_logout)
cmd_grp_cli.add_command(cmd_grp_list)
cmd_grp_cli.add_command(cmd_download_artefact)
cmd_grp_list.add_command(cmd_nodes)
cmd_grp_list.add_command(cmd_messages)
cmd_grp_list.add_command(cmd_content)


def get_new_session(url, credentials):
    session = requests.session()
    session.headers.update({'X-CSRF-Token': 'fetch'})
    session.headers.update({'User-Agent': 'Apache-HttpClient/4.3.6 (java 1.5)'})
    response = session.head(url, auth=credentials)
    if response.status_code == 200 and response.headers['X-CSRF-Token']:
        return response
    else:
        print(red("Error at log in, couldn't fetch CSRF"))
        return False


def set_session(user, password, api_url, cmd_url):
    credentials = requests.auth.HTTPBasicAuth(user, password)

    try:
        api_response = get_new_session(api_url, credentials)
        cmd_response = get_new_session(cmd_url, credentials)
    except Exception as e:
        print(red("Error at log in, check your login data"))
        raise SystemExit(0)

    if api_response and cmd_response:
        session_data = {
            "api_url": api_url,
            "api_token": api_response.headers['X-CSRF-Token'],
            "api_cookies": api_response.cookies,
            "cmd_url": cmd_url,
            "cmd_token": cmd_response.headers['X-CSRF-Token'],
            "cmd_cookies": cmd_response.cookies
        }
        persist_current_session(session_data)
        print(green('Logged in'))
        return session_data
    else:
        print(red("Error at log in"))
        raise SystemExit(0)


def persist_current_session(session_data):
    with open(expanduser('~') + constants.SESSION_FILE, 'wb') as file:
        pickle.dump(session_data, file)


def restore_current_session():
    try:
        with open(expanduser('~') + constants.SESSION_FILE, 'rb') as file:
            session_data = pickle.load(file)
        return session_data
    except OSError:
        print(red('You are not logged in'))
        raise SystemExit(0)


def remove_current_session():
    if os.path.exists(expanduser('~') + constants.SESSION_FILE):
        os.remove(expanduser('~') + constants.SESSION_FILE)
        print("Bye!")
    else:
        print("You were not logged in")


def modify_current_session(parameter, value):
    session_data = restore_current_session()
    session_data[parameter] = value
    persist_current_session(session_data)


def download_iflow(symbolic_name):
    session_data = restore_current_session()
    artefact_id = get_artefact_id(symbolic_name)
    response = call_command('com.sap.it.nm.commands.deploy.DownloadContentCommand', (), {
        'tenantId': session_data["account_details"]["id"],
        'artifactIds': artefact_id
    })
    doc = ElementTree.fromstring(response.content.decode(constants.ENCODING))
    content = doc.find('.//content')
    bin_content = base64.b64decode(content.text)
    try:
        with open(symbolic_name + '.zip', "wb") as file:
            file.write(bin_content)

        with zipfile.ZipFile(symbolic_name + '.zip', "r") as zip_ref:
            zip_ref.extractall("./" + symbolic_name)
    except Exception as e:
        print(red("Error at downloading, check your permissions"))
        raise SystemExit(0)



def get_artefact_id(symbolic_name):
    session_data = restore_current_session()
    response = call_command('com.sap.it.nm.commands.deploy.ListContentCommand', (), {
        'tenantId': session_data["account_details"]["id"],
        'symbolicName': symbolic_name
    })
    doc = ElementTree.fromstring(response.content.decode(constants.ENCODING))
    try:
        artefact_id = doc.find('./artifactDescriptors').attrib["id"]
        return artefact_id
    except Exception as e:
        print(red("Problem at reading, artefact id, not found?"))
        raise SystemExit(0)


def get_integration_content(args):
    query = {'$format': 'json'}

    response = call_operation(constants.INT_CONTENT, query=query)
    doc = json.loads(response.content.decode(constants.ENCODING))
    table_data = []

    if '__next' in doc['d']:
        doc['d']['results'] = get_more_messages(doc['d']['__next'], doc['d']['results'])

    for e in doc['d']['results']:
        if e['Status'] == 'STARTED':
            e['Status'] = green(e['Status'])
        elif e['Status'] == 'ERROR':
            e['Status'] = red(e['Status'])

        table_data.append([
            e['Status'],
            format_json_date(e['DeployedOn']),
            e['DeployedBy'],
            e['Type'],
            e['Id'],
            e['Version']
        ])

    # The odata services does not provides sorting or filtering. Manually implemented.
    tmp_table = list()
    if not args['from']:
        args['from'] = datetime(1900, 1, 1)
    if not args['to']:
        args['to'] = datetime(9999, 12, 31)

    for line in table_data:
        if not (
                (datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f') >= args['from'])
                and
                (datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f') <= args['to'])
        ):
            continue

        if args['iflows'] and line[3] == 'INTEGRATION_FLOW':
            tmp_table += [line]
            continue
        elif args['odata'] and line[3] == 'ODATA_SERVICE':
            tmp_table += [line]
            continue
        elif args['value_mapping'] and line[3] == 'VALUE_MAPPING':
            tmp_table += [line]
            continue
        elif not (args['iflows'] or args['odata'] or args['value_mapping']):
            tmp_table += [line]

    table_data = tmp_table
    table_data.sort(key=lambda artefact: artefact[1])
    table_data = [['Status', 'Deployed On', 'Deployed by', 'Type', 'ID', 'Version']] + table_data
    table_data.append(['TOTAL', str(len(table_data) - 1) + ' Artefacts'])
    table = AsciiTable(table_data)
    table.title = '---Deployed Artefacts'
    table.inner_footing_row_border = True
    print(table.table)


def get_messages(args):
    query = {'$format': 'json',
             '$orderby': 'LogStart'}

    if args['top'] is not None:
        query['$top'] = args['top']

    filter_str = None
    first_filter = True
    last_operator = None
    par_count = 0
    for filter in constants.FILTER_MESSAGES:
        params = constants.FILTER_MESSAGES[filter]
        if first_filter and args[filter]:
            first_filter = False
            filter_str = format_query_string(params, args[filter])
            last_operator = params[0]
        elif args[filter]:
            filter_str += '%s(%s' % (last_operator, format_query_string(params, args[filter]))
            last_operator = params[0]
            par_count += 1

    for x in range(par_count):
        filter_str += ')'

    if filter_str:
        query['$filter'] = filter_str

    response = call_operation(constants.MSG_LOGS, query=query)
    doc = json.loads(response.content.decode(constants.ENCODING))
    if '__next' in doc['d']:
        doc['d']['results'] = get_more_messages(doc['d']['__next'], doc['d']['results'])

    table_data = [['Status', 'Start on', 'End on', 'Message GUID', 'iFlow name']]
    for e in doc['d']['results']:
        if e['Status'] == 'COMPLETED':
            e['Status'] = green(e['Status'])
        elif e['Status'] == 'FAILED':
            e['Status'] = red(e['Status'])

        table_data.append([
            e['Status'],
            format_json_date(e['LogStart']),
            format_json_date(e['LogEnd']),
            e['MessageGuid'],
            e['IntegrationFlowName']
        ])
    table_data.append(['TOTAL', str(len(table_data) - 1) + ' Messages'])
    table = AsciiTable(table_data)
    table.title = '---Selected Messages'
    table.inner_footing_row_border = True
    print(table.table)


def get_more_messages(url, results):
    response = call_operation(url=url)
    doc = json.loads(response.content.decode(constants.ENCODING))
    if '__next' in doc['d']:
        doc['d']['results'] = get_more_messages(doc['d']['__next'], doc['d']['results'])
    results += doc['d']['results']
    return results


def call_operation(operation=None, method="GET", query={'$format': 'json'}, payload=None, url=None):
    session_data = restore_current_session()
    session = requests.session()
    session.headers.update({'X-CSRF-Token': session_data['api_token']})
    session.cookies = session_data['api_cookies']
    if url:
        api_url = url
    else:
        api_url = session_data["api_url"] + operation + '?' + urlencode(query)
    response = None
    if (method == 'POST') & (payload is not None):
        response = session.post(api_url, payload)
    elif method == 'GET':
        response = session.get(api_url)
    else:
        print(red("Method/Payload do not supported"))
        raise SystemExit(0)
    if response.status_code < 300:
        return response
    else:
        print(red("Error at calling the operation. Please log in again."))
        raise SystemExit(0)


def get_node_list(display=True):
    response = call_command(
        'com.sap.it.op.srv.commands.dashboard.ParticipantListCommand',
        {'withActiveTenants': 'false'},
        {'onlyHeader': 'false', 'withAdminNodes': 'true', 'withNodes': 'true'}
    )

    doc = ElementTree.fromstring(response.content.decode(constants.ENCODING))
    account_details = {
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
        account_details['nodes'].append(det)

    modify_current_session("account_details", account_details)
    if display:
        print(blue('Account Type:\t'), end='')
        print(account_details['type'], end='\t')
        print(blue('Version:\t'), end='')
        print(account_details['version'])
        print(blue('Account ID:\t'), end='')
        print(account_details['id'], end='\t')
        print(blue('Account Name:\t'), end='')
        print(account_details['name'])
        table_data = [['Node ID', 'Name', 'Version', 'State', 'Type']]
        for node in account_details['nodes']:
            table_data.append([
                node['id'],
                node['name'],
                node['version'],
                node['state'],
                node['type']
            ])
        table = AsciiTable(table_data)
        table.title = '---' + blue('Account Nodes')
        print(table.table)


def call_command(command, attributes, variables):
    session_data = restore_current_session()
    session = requests.session()
    session.headers.update({'X-CSRF-Token': session_data['cmd_token']})
    session.headers.update({'User-Agent': 'CMD-CLIENT HCI-Eclipse/1.65'})
    session.cookies = session_data['cmd_cookies']
    command_url = session_data["cmd_url"] + '/' + command
    command_payload = create_command_payload(command, attributes, variables)
    response = session.post(command_url, command_payload)
    if response.status_code < 300:
        return response
    else:
        print(red("Error at calling the command. Please log in again."))
        raise SystemExit(0)


def create_command_payload(command, attributes, variables):
    root = Element(command)
    for attr in attributes:
        root.set(attr, attributes[attr])
    for var in variables:
        variable = SubElement(root, var)
        variable.text = variables[var]
    return tostring(root, 'utf-8')


def line(texts, separated_by=''):
    final = ''
    for text in texts:
        final += text + separated_by
    return final


def format_json_date(json_date):
    dd = decimal.Decimal(''.join(i for i in json_date if i.isdigit()))
    s, ms = divmod(dd, 1000)
    return '%s.%03d' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(s)), ms)


def format_query_string(params, value):
    variable = params[1]
    comparision = params[2]
    string = variable + ' ' + comparision + ' '
    if isinstance(value, datetime):
        string += 'datetime\'' + value.strftime('%Y-%m-%dT%H:%M:%S') + '\''
    elif isinstance(value, bool):
        return string
    else:
        string += str(value)
    return string


def show_copyright():
    print('\n%s\n\n%s\n%s\n%s\n' % (
        warning(constants.DISCLAIMER),
        constants.VERSION,
        constants.LICENSE,
        constants.COPYRIGHT
    ))


if __name__ == '__main__':
    cmd_grp_cli()
