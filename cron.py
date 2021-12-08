import uuid

from services import google_helper
from services import config_helper
from google.cloud import bigquery
from datetime import datetime
import logging
import utils
import custom_logging

LOG = custom_logging.add_json_log_streaming(logging.getLogger(__name__))
BIGQUERY_TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S.%f'


def process_user_mail_purge(job_id, user_email, older_than_days, commit=False):
    log_context = dict(context=locals().copy())
    log_line_prefix = '[{}][{}] '.format(job_id, 'COMMIT' if commit else 'DRYRUN')
    LOG.debug('{}Processing mail purge for user: {}'.format(log_line_prefix, locals()), extra=log_context)
    # build a gmail service for this user

    LOG.debug(f'{log_line_prefix}[{user_email}] Building services...', extra=log_context)
    mail_svc = google_helper.build_service_gmail(user_email)
    bq_svc = bigquery.Client(credentials=google_helper.build_credentials(scopes=['https://www.googleapis.com/auth/bigquery']))
    config = config_helper.fetch_config()

    # find all messages older than X.
    LOG.debug(f'{log_line_prefix}[{user_email}] Searching mail older than {older_than_days} days...')
    old_emails = google_helper.list_emails_older_than(mail_svc, older_than_days)

    LOG.debug(f'{log_line_prefix}[{user_email}] Found {len(old_emails)} emails to purge...', extra=log_context)
    # purge each message. TODO: future enhancement - update to batch delete for performance
    for idx, email in enumerate(old_emails):
        # parameters
        google_msg_id = email['id']  # google message ID is not the RFC message ID.

        # fetch message itself by Google message ID, so we can grab interesting metadata (message ID, timestamp, etc)
        msg_data = mail_svc.users().messages().get(userId='me', id=google_msg_id, format='metadata', metadataHeaders=['message-id']).execute(num_retries=google_helper.DEFAULT_GOOGLE_API_NUM_RETRIES)

        # parse out metadata that we want, namely a timestamp and a message ID
        msg_timestamp = datetime.fromtimestamp(int(msg_data['internalDate']) / 1000)
        headers = msg_data['payload']['headers']
        msg_id = [h['value'] for h in headers if h['name'].lower()=='message-id']
        if not msg_id:
            LOG.error(f'{log_line_prefix}[{user_email}] Could not find message ID for {idx+1} of {len(old_emails)} with message ID: {msg_id}. Skipping ...', extra=log_context)
            continue
        else:
            msg_id = msg_id[0]


        # delete the message if commit is on
        if commit:
            LOG.debug(f'[{user_email}] Deleting email {idx + 1} of {len(old_emails)} with message ID: {msg_id}...', extra=log_context)
            mail_svc.users().messages().delete(userId='me', id=email['id']).execute(num_retries=3)
        else:
            LOG.debug(f'[{user_email}] (Skipping) Deleting email {idx + 1} of {len(old_emails)} with message ID: {msg_id}...', extra=log_context)

        # write to BQ.
        bq_table_id = config['BIGQUERY_TABLE_NAME']
        row_data = dict(job_id=job_id, msg_id=msg_id, msg_timestamp=msg_timestamp.strftime(BIGQUERY_TIMESTAMP_FMT), delete_timestamp=datetime.now().strftime(BIGQUERY_TIMESTAMP_FMT), account=user_email, commit=commit)
        errors = bq_svc.insert_rows_json(bq_table_id, [row_data], row_ids=[None] )  # Make an API request.
        if not errors:
            LOG.debug(f'{log_line_prefix}[{user_email}] Inserted row to BQ: {row_data}', extra=log_context)
        else:
            LOG.error(f'{log_line_prefix}[{user_email}] Encountered errors while inserting rows: {errors}', extra=log_context)
        pass


def process_all_users_mail_purge():
    '''
    Finds every user in the domain, determines each users retention policy, and kicks off a purge job for that retention period for that user.
    :return:
    '''
    # load config
    job_id = uuid.uuid4().hex
    log_context = dict(context=locals().copy())
    log_line_prefix = '[{}] '.format(job_id)


    LOG.debug(f'{log_line_prefix}Loading config', extra=log_context)
    config = config_helper.fetch_config()
    LOG.debug(f'{log_line_prefix}Config dump: {config!r}', extra=log_context)

    # make any assertions we care about
    assert config['USER_SCOPE'], 'User list is not set in config. It should be a list of email addresses, or "all".'
    assert config.get('BIGQUERY_TABLE_NAME', '').strip(), 'BigQuery Table Name needed to write results to'

    # find all users, and their OUs
    LOG.debug(f'{log_line_prefix}Fetching metadata about domain', extra=log_context)
    org_svc = google_helper.build_service_org_directory(config['ADMIN_USER'])
    org_users = google_helper.list_users(org_svc)
    org_units = google_helper.list_org_units(org_svc)  # maps OU ID > OU object
    org_units_by_path = { o['orgUnitPath']:o for o in org_units.values() }  # maps OU Path > OU object

    # determine if we should be looking at a filtered set of users, based on config
    if 'all' in config['USER_SCOPE']:
        # -- no filtering required
        pass
    else:
        # -- only include users listed in the user_scope
        org_users = list(filter(lambda u: utils.normalize_email(u['primaryEmail']) in config['USER_SCOPE'], org_users))


    LOG.debug(f'{log_line_prefix}Found {len(org_users)} users to process', extra=log_context)
    for idx, user in enumerate(org_users):
        # grab metadata that is important to us
        LOG.debug(f'{log_line_prefix}[{idx} of {len(org_users)}] Processing user with metadata {user}', extra=log_context)
        user_ou_path = user['orgUnitPath']
        user_email = user['primaryEmail']
        user_ou_id = org_units_by_path.get(user_ou_path, {}).get('orgUnitId')

        # find retention period for user
        user_retention_days = config['RETENTION_OVERRIDES_BY_OU_ID'].get(user_ou_id, config['DEFAULT_RETENTION_DAYS'])

        # process user mail deletion
        process_user_mail_purge(job_id, user_email, user_retention_days, config['COMMIT'])

    LOG.debug(f'{log_line_prefix}Completed processing {len(org_users)}  users', extra=log_context)


def healthcheck():
    '''
    Checks BigQuery to make sure we've deleted a certain number of emails in the last X hours.
    :return:
    '''

    config = config_helper.fetch_config()
    bq_svc = bigquery.Client(credentials=google_helper.build_credentials(scopes=['https://www.googleapis.com/auth/bigquery']))

    # build bigquery query to see what's been deleted recently
    query_24hr_job = bq_svc.query(f'''
        SELECT COUNT(*) as recent_deletions FROM {config["BIGQUERY_TABLE_NAME"]} WHERE TIMESTAMP(delete_timestamp) > DATE_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR) AND `commit`
    ''')
    recent_deletions_ct = list(query_24hr_job.result())[0].recent_deletions

    # if below threshold, throw an error.
    if recent_deletions_ct < config['HEALTHY_DELETIONS_THRESHOLD_PER_DAY']:
        LOG.error(f'HEALTH_CHECK_FAILED. In the last 24 hours, {recent_deletions_ct} emails were deleted, below the threshold of {config["HEALTHY_DELETIONS_THRESHOLD_PER_DAY"]}', extra=dict(origin='healthcheck', test='HEALTHY_DELETIONS_THRESHOLD_PER_DAY', status='HEALTH_CHECK_FAILED'))

    else:
        LOG.info(f'HEALTH_CHECK_PASSED. In the last 24 hours, {recent_deletions_ct} emails were deleted, above the threshold of {config["HEALTHY_DELETIONS_THRESHOLD_PER_DAY"]}', extra=dict(origin='healthcheck', test='HEALTHY_DELETIONS_THRESHOLD_PER_DAY', status='HEALTH_CHECK_PASSED'))

        
