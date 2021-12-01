## Setup
1. Create GCP project
2. Create service account in GCP project.
3. Enable Gmail and Admin SDK in GCP project
4. Give service account address BigQuery Editor, BigQuery Job User and Firebase access in GCP IAM.
5. Give client ID for service account access to the following scopes under Domain Wide Delegation in the Workspace Admin panel:
    ```
    https://www.googleapis.com/auth/admin.directory.orgunit,https://www.googleapis.com/auth/admin.directory.user.readonly,https://mail.google.com/
    ```
6. Create BQ Dataset, and a BQ table with the following Schema
    ```
    job_id:STRING,
    msg_id:STRING,
    account:STRING,
    msg_timestamp:DATETIME,
    delete_timestamp:DATETIME,
    commit:BOOLEAN
    ```
7. Enable Datastore in Native mode with collection `GLOBAL` and blank object with doc ID `CONFIG` 
8. Deploy to Cloud Run
   - Create a Cloud Run Service
   - "Set up with Cloud Build" using Github, Branch=^master$, and Build Type=Dockerfile
   - Cap Autoscaling to 2 instances
   - Under Advanced Settings > Security, set the service account to the one created above.
   - Allow internal traffic and traffic from Cloud Load Balancing
   - Allow unauthenticated invocations

## Optional setup
1. In Cloud Monitoring, set up alerts for health check failures. You can use the `log_context`.{`origin`,`test`, and `status`} fields to search. Likely, you are looking for `status=="HEALTH_CHECK_FAILED"`

## Local development
You can of course run & build the Docker container locally. Alternatively, while perhaps not ideal, you can:
1. set up a python virtual environment
2. download the service account JSON key locally (don't commit back to repo)
3. `pip install -r requirements.txt`
4. `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
5. `python app.py`

## Future
- Parallelize for larger workloads
- More constructive handling of request timeout limits. For example, at the time of writing, Cloud Run caps requests at 1 hour. This isn't strictly an issue, but alternative approaches may be desired. 

## TODO
- CI/CD -- Keep this in GCP, or use CircleCI. Want one click deploy for code changes. Schema changes can be dealt with manually or by migration scripts, etc.
- Clean up README
- Integrate with Pagerduty (post-deploy)


DONE:
- Add dry-run facility
- Query actual message to get message ID and timestamp
- Add "debug mode" -- allows for comma separated entry of users to run automation against.
- Settings page UI -- use bootstrap
- Structured log entries {user, jobId, message, logLevel}