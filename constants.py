VERSION = 'CPI-CLI V/0.0.1 Alpha'
LICENSE = 'MIT License - https://opensource.org/licenses/MIT'
COPYRIGHT = '2019 - Ariel Bravo Ayala - http://bit.ly/AMBA-CPI'
DISCLAIMER = 'DISCLAIMER: For demo only - Use it at your own risk!'

SESSION_FILE = '/.cpi-cli-session'
PARTICIPANT_LIST = 'com.sap.it.op.srv.commands.dashboard.ParticipantListCommand'
ENCODING = 'UTF-8'
MSG_LOGS = 'MessageProcessingLogs'
INT_CONTENT = 'IntegrationRuntimeArtifacts'
CREDENTIALS = 'UserCredentials'

TOP_MESSAGES = {
    'top': ['$top', '', '=']
}
FILTER_MESSAGES = {
    'from': [' and ', 'LogStart', 'ge'],
    'to': [' and ', 'LogStart', 'le'],
    'success': [' or ', 'Status', 'eq \'COMPLETED\''],
    'errors': [' or ', 'Status', 'eq \'FAILED\'']
}
FILTER_CONTENTS = {
    'from': [' and ', 'DeployedOn', 'ge'],
    'to': [' and ', 'DeployedOn', 'le'],
    'iflows': [' or ', 'Type', 'eq \'INTEGRATION_FLOW\''],
    'odata': [' or ', 'Type', 'eq \'ODATA_SERVICE\''],
    'valuemapping': [' or ', 'Type', 'eq \'VALUE_MAPPING\'']
}
