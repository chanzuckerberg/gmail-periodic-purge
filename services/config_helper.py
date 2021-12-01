from google.cloud import firestore
from services import google_helper

DEFAULT_CONFIG = {
    'BIGQUERY_TABLE_NAME': '',
    'ADMIN_USER': '',
    'DEFAULT_RETENTION_DAYS': 180,
    'HEALTHY_DELETIONS_THRESHOLD_PER_DAY': 100,
    'RETENTION_OVERRIDES_BY_OU_ID': {
    },
    'USER_SCOPE': [

    ],
    'COMMIT': False
}


def build_firestore_client():
    return firestore.Client(credentials=google_helper.build_credentials(scopes=['https://www.googleapis.com/auth/datastore']))


def fetch_config():
    '''

    :return: dict, config object from DB.
    '''

    db = build_firestore_client()
    doc_ref = db.collection(u'GLOBAL').document(u'CONFIG')
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return DEFAULT_CONFIG


def set_config(config):
    '''

    :param config: dict, config object to push to DB
    :return: None
    '''
    db = build_firestore_client()
    doc_ref = db.collection(u'GLOBAL').document(u'CONFIG')
    return doc_ref.set(config)