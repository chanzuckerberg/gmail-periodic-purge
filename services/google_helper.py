from google.oauth2 import service_account
import google.auth
from googleapiclient.discovery import build
import logging
from datetime import date, timedelta
import os
from google.cloud import secretmanager
import functools
import json

DEFAULT_GOOGLE_API_NUM_RETRIES = 3
LOG = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def fetch_secret_cached(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_name)
    service_account_json = response.payload.data.decode("UTF-8")
    return service_account_json


@functools.lru_cache(maxsize=1)
def fetch_project_id():
    credentials, project_id = google.auth.default()
    return project_id


def build_credentials(scopes, impersonate=None):
    '''

    :param scopes: list of scopes
    :param impersonate: email address of account to impersonate, or None.
    :return: credential object for use with API service
    '''

    project_id = fetch_project_id()
    secret_name = f"projects/{project_id}/secrets/AUTOMATION_SERVICE_ACCOUNT/versions/latest"
    service_account_info = json.loads(fetch_secret_cached(secret_name))
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
    if impersonate:
        credentials = credentials.with_subject(impersonate)
    return credentials


def build_service(service_name, service_version, impersonate_email, scopes):
    '''

    :param service_name: string, name of the service.
    :param service_version: string, the version of the service.
    :param impersonate_email: string, email address of account to impersonate, or None.
    :param scopes: list, the set of scopes needed
    :return:
    '''
    service = build(service_name, service_version, credentials=build_credentials(scopes=scopes, impersonate=impersonate_email))
    service._impersonate_email = impersonate_email
    return service


def build_service_gmail(user_email):
    '''
    Single purpose service builder for read/write access to Gmail.
    :param user_email:
    :return:
    '''
    svc = build_service('gmail', 'v1', user_email, scopes=['https://mail.google.com/'])
    return svc


def build_service_org_directory(user_email):
    '''
    Single purpose service builder for read access to directory
    :param user_email:
    :return:
    '''
    return build_service('admin', 'directory_v1', user_email, scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly', 'https://www.googleapis.com/auth/admin.directory.orgunit'])


def list_org_units(svc):
    '''
    :param svc: API service, authorized to list org units on domain
    :return: dict, orgUnitId -> org unit
    '''


    LOG.info("Fetching orgunits list from Google Workspace")
    orgunits = []
    orgunit_lookup = {}
    results = svc.orgunits().list(customerId='my_customer', orgUnitPath='/', type='all').execute(num_retries=DEFAULT_GOOGLE_API_NUM_RETRIES)
    orgunits.extend(results.get('organizationUnits', []))

    LOG.info("Found {} total orgunits in Google Workspace".format(len(orgunits)))

    LOG.debug("Building orgunit mapping")

    for orgunit in orgunits:
        orgunit_lookup[orgunit['orgUnitId']] = orgunit

    LOG.debug("Completed orgunit mapping")

    return orgunit_lookup


def list_users(svc):
    '''
    :param svc: API service, authorized to list user accounts on domain
    :return: list of users
    '''
    LOG.info("Fetching user list from Google Workspace")
    users = []
    page_token = None
    while True:
        results = svc.users().list(pageToken=page_token, customer='my_customer', orderBy='email', maxResults=500).execute(num_retries=DEFAULT_GOOGLE_API_NUM_RETRIES)
        users.extend(results.get('users', []))
        LOG.debug("  .. {} users so far.".format(len(users)))
        page_token = results.get('nextPageToken', None)
        if not page_token:
            break

    LOG.info("Found {} total users in Google Workspace".format(len(users)))

    return users


def list_emails_older_than(svc, older_than_days):
    '''
    :param svc: API service, authorized to read email metadata across domain
    :param older_than_days: integer, find all messages older than (now() minus <older_than_days> days)
    :return: list of message objects (id, threadId)
    '''

    emails = []
    page_token = None
    upper_date = date.today() - timedelta(days=older_than_days+1)
    message_query = 'before:{}'.format(upper_date.strftime('%Y/%m/%d'))
    while True:
        results = svc.users().messages().list(pageToken=page_token, userId='me', q=message_query, maxResults=500).execute(num_retries=DEFAULT_GOOGLE_API_NUM_RETRIES)
        emails.extend(results.get('messages', []))
        LOG.debug("  .. {} emails so far.".format(len(emails)))
        page_token = results.get('nextPageToken', None)
        if not page_token:
            break

    LOG.info("[{}] Found {} total emails in Google Workspace with query: {}".format(svc._impersonate_email, len(emails), message_query))

    return emails


def get_mail_message(svc, google_msg_id, fields='id,payload,internalDate'):
    '''
    :param svc: API service, authorized to read email metadata across domain
    :param google_msg_id: string, message ID.
    :param fields: string, field projection to return.
    :return: message object
    '''

    return svc.users().messages().get(userId='me', id=google_msg_id, fields=fields).execute(num_retries=DEFAULT_GOOGLE_API_NUM_RETRIES)



