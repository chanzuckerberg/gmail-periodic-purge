"""

"""
import os
from flask import Flask, render_template, request

import utils
from services import google_helper
from services import config_helper
import logging
from pprint import pprint
import sys
import re
import custom_logging

# pylint: disable=C0103
app = Flask(__name__)
LOG = custom_logging.add_json_log_streaming(logging.getLogger(__name__))

@app.route('/health', methods=['GET'])
def health():
    return 'Up and running!'

@app.route('/', methods=['GET', 'POST'])
def settings():
    """This app only has a single page, which is the settings page."""

    # -- fetch settings from Firestore.
    config = config_helper.fetch_config()

    # -- fetch a list of all OUs from Google.
    if config['ADMIN_USER']:
        org_svc = google_helper.build_service_org_directory(config['ADMIN_USER'])
        ou_map = google_helper.list_org_units(org_svc)
    else:
        ou_map = {}

    # -- merge list of Google OUs into settings dict to make sure all OUs are represented for UI rendering
    ou_overrides = config.setdefault('RETENTION_OVERRIDES_BY_OU_ID', {})
    for ou_id in ou_map:
        ou_overrides.setdefault(ou_id, None)

    # -- merge in POST data
    if request.method == 'POST':
        config['BIGQUERY_TABLE_NAME'] = request.form.get('general_bigquery_table_name', '').strip()
        config['ADMIN_USER'] = request.form.get('general_workspace_admin', '').strip()
        config['DEFAULT_RETENTION_DAYS'] = request.form.get('general_default_retention', type=int)
        config['HEALTHY_DELETIONS_THRESHOLD_PER_DAY'] = request.form.get('general_healthy_deletion_threshold', type=int)
        config['COMMIT'] = request.form.get('general_commit_enabled')=='on'

        for key, value in request.form.items():
            if key.startswith('ou_override__'):
                ou_id = key.replace('ou_override__', '')
                ou_value = int(value) if value else None
                ou_overrides[ou_id] = ou_value

        # as we save the user list, translate it from delimited to list format, filtering out empties, and normalizing each entry to lowercase
        # normalization generally useful for comparisons
        config['USER_SCOPE'] = list(filter(bool, map(utils.normalize_email, re.split('\n|,|;', request.form.get('general_user_scope') or '')))) or ['all']

        # save to database
        config_helper.set_config(config)

    # -- ready to render
    return render_template('index.html', **locals())



if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(port=server_port, host='0.0.0.0')
