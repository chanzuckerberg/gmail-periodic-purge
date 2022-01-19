# gmail-periodic-purge
(Unstable Project) A cron job that will purge old emails from G-mail. Mainly used when there are legal holds placed in Google Workspace Vault.


## Setup
1. Create GCP project
2. Create service account in GCP project.
3. Enable the following APIs 
   1. Gmail API
   2. Admin SDK API
   3. App Engine Admin API
   4. Cloud Build API
   5. Compute Engine API
   6. Cloud Deployment Manager API V2
   7. BigQuery API
   8. Cloud Scheduler API
   9. Cloud Firestore API
   10. Cloud Identity-Aware Proxy API
   
4. Give service account address BigQuery Data Editor, BigQuery Job User and Cloud DataStore User in GCP IAM.
5. Give client ID for service account access to the following scopes under Domain Wide Delegation in the Workspace Admin panel:
    ```
    https://www.googleapis.com/auth/admin.directory.orgunit,https://www.googleapis.com/auth/admin.directory.user.readonly,https://mail.google.com/
    ```
6. Download Service Account credential, and save to `AUTOMATION_SERVICE_ACCOUNT` in GCP's Secret Manager
7. Create BQ Dataset, and a BQ table with the following Schema
    ```
    job_id:STRING,
    msg_id:STRING,
    account:STRING,
    msg_timestamp:DATETIME,
    delete_timestamp:DATETIME,
    commit:BOOLEAN
    ```
8. In IAM, give the AppEngine default service account Secret Manager Secret Accessor perms
9. Within Cloud Build ensure that App Engine access is turned on under Settings
10. Create Cloud Build Trigger using Github, Branch=^master$, Build Type=CloudBuild, location=`/triggers/cloudbuild.yaml`)
11. Turn on IAP
    1. Configure Consent Screen
    3. Add any other users that need access
12. Create Cloud Scheduler config
    1. Add above-created service account as an IAP-Secured Web App User
    2. HTTP GET `https://APPENGINE_URL/cron/daily`
    3. Add OIDC Auth header (only required if you enabled IAP)
    4. Use above-created service account
    5. For `Audience`, grab Oauth client ID that was autogenerated by IAP from here https://console.cloud.google.com/apis/credentials

## Optional setup
1. In Cloud Monitoring, set up alerts for health check failures. You can use the `log_context`.{`origin`,`test`, and `status`} fields to search. Likely, you are looking for `status=="HEALTH_CHECK_FAILED"`. Alternatively, a query like this would work as well:
```
resource.type="gae_app"
log_name:"/logs/appengine.googleapis.com%2Fstdout"
jsonPayload.message:"HEALTH_CHECK_FAILED"
```

It is also useful to capture certain runtime exceptions. 
```
resource.type="gae_app"
log_name:"/logs/appengine.googleapis.com%2Fstdout"
jsonPayload.message:"NOTIFY_EXCEPTION"
```


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
- User interface could use some work, namely validation and helpful prompts.
- More automation for initial deployment.

## Security

Please note: If you believe you have found a security issue, please responsibly disclose by contacting us at security@chanzuckerberg.com.


## Contributing

Contributions and ideas are welcome! Please see [our contributing guide](CONTRIBUTING.md) and don't hesitate to open an issue or send a pull request to improve the functionality of this gem.

This project adheres to the Contributor Covenant [code of conduct](https://github.com/chanzuckerberg/.github/tree/master/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to opensource@chanzuckerberg.com.

## License

[MIT](https://github.com/chanzuckerberg/sorbet-rails/blob/master/LICENSE)


