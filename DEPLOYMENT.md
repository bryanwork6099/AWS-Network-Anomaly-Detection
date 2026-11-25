# Deployment Guide

This document describes the deployment layout and configuration for the
AWS Network Anomaly Detection project.

> **Important:** This guide documents the deployed implementation and
> the configuration values recorded during development. It is not a
> one-command infrastructure deployment. AWS resources were provisioned
> and configured through the AWS Console, CLI, and project-specific
> deployment steps. Review the actual source files and AWS account
> before repeating any deployment.

## 1. Environment

  Setting                Value
  ---------------------- ------------------------------------------------------
  AWS Region             `ap-southeast-1`
  AWS account            Use your own account; do not copy another account ID
  Kinesis stream         `network-traffic-stream-v3`
  DynamoDB table         `network-anomaly-aggregation-v3`
  Finalizer Lambda       `network-anomaly-window-finalizer`
  Scorer Lambda          `network-anomaly-scorer`
  API Lambda             `network-anomaly-api`
  SageMaker endpoint     `network-anomaly-rcf-v3-serverless-endpoint`
  API Gateway REST API   `network-anomaly-rest-api`
  API Gateway stage      `prod`
  Git branch             `main`

## 2. Prerequisites

-   An AWS account with permissions to create and configure the required
    services.
-   AWS CLI installed and configured with an appropriately scoped IAM
    identity.
-   Python version compatible with the Lambda packages and local
    project.
-   Node.js and npm for the React/Vite frontend.
-   Git.
-   Access to the GitHub repository.

Check local tools:

``` powershell
aws --version
python --version
node --version
npm --version
git --version
```

Check the active AWS identity and region:

``` powershell
aws sts get-caller-identity
aws configure get region
```

The examples use `ap-southeast-1`. Ensure the CLI profile and region are
correct before running AWS commands.

## 3. Deployment order

The logical deployment order is:

1.  Create the Kinesis stream and DynamoDB aggregation table, including
    its GSI and TTL configuration.
2.  Deploy the Kinesis consumer Lambda and configure its Kinesis event
    source mapping.
3.  Deploy the window-finalizer Lambda and configure EventBridge
    Scheduler.
4.  Train the Random Cut Forest model, create the SageMaker model and
    serverless endpoint.
5.  Deploy the anomaly-scorer Lambda, configure its environment
    variables and permissions, and connect it to DynamoDB Streams.
6.  Deploy the API Lambda and configure API Gateway.
7.  Configure and deploy the React frontend through AWS Amplify.
8.  Run normal and suspicious traffic tests and verify the results
    across the pipeline.

The order matters because downstream functions depend on resources
created earlier.

## 4. Core AWS configuration

### 4.1 Amazon Kinesis Data Streams

Implemented stream:

``` text
network-traffic-stream-v3
```

Recorded settings: - Region: `ap-southeast-1` - Capacity: On-demand -
Retention: 24 hours - Shards: 4

Verify the stream:

``` powershell
aws kinesis describe-stream-summary `
  --stream-name network-traffic-stream-v3 `
  --region ap-southeast-1
```

### 4.2 Amazon DynamoDB

Implemented table:

``` text
network-anomaly-aggregation-v3
```

The table uses a string partition key and string sort key, on-demand
billing, a GSI named `GSI1-OpenWindowsByFinalizeAt`, TTL, and deletion
protection.

Inspect the table:

``` powershell
aws dynamodb describe-table `
  --table-name network-anomaly-aggregation-v3 `
  --region ap-southeast-1
```

Inspect TTL:

``` powershell
aws dynamodb describe-time-to-live `
  --table-name network-anomaly-aggregation-v3 `
  --region ap-southeast-1
```

### 4.3 EventBridge Scheduler and finalizer

The finalizer Lambda is:

``` text
network-anomaly-window-finalizer
```

The EventBridge Scheduler schedule is:

``` text
network-anomaly-window-finalizer-schedule
```

It runs at a rate of one minute with the flexible time window disabled.
Confirm the schedule target role can invoke the Lambda and that the
Lambda can query/update the DynamoDB table.

### 4.4 SageMaker model and endpoint

The deployed inference endpoint is:

``` text
network-anomaly-rcf-v3-serverless-endpoint
```

Recorded model configuration: - Algorithm: Random Cut Forest - Feature
dimension: 10 - Number of trees: 100 - Samples per tree: 256 -
Serverless memory: 2048 MB - Maximum concurrency: 1 - Model version
label: `rcf-v3`

The training artifact was stored in S3. The original project artifact
location was:

``` text
s3://aws-network-anomaly-detection-366554472163/model-artifacts/rcf-v3/network-anomaly-rcf-v3-20261124/output/model.tar.gz
```

This S3 URI is account- and project-specific. Verify that the bucket and
object still exist before reusing it. Do not assume the training job or
endpoint can be recreated solely from the artifact URI.

### 4.5 Anomaly scorer Lambda

Function:

``` text
network-anomaly-scorer
```

Recorded environment variables:

  Variable              Value
  --------------------- ----------------------------------------------
  `TABLE_NAME`          `network-anomaly-aggregation-v3`
  `ENDPOINT_NAME`       `network-anomaly-rcf-v3-serverless-endpoint`
  `MODEL_VERSION`       `rcf-v3`
  `ANOMALY_THRESHOLD`   `2.980612`

The Lambda role needs narrowly scoped permissions to read DynamoDB
Stream records, update the aggregation table, and invoke the SageMaker
endpoint. The DynamoDB Stream was configured with `NEW_AND_OLD_IMAGES`;
the event source mapping used batch size 1 and starting position
`LATEST`.

### 4.6 API Lambda and API Gateway

API Lambda:

``` text
network-anomaly-api
```

Environment variable:

``` text
TABLE_NAME=network-anomaly-aggregation-v3
```

REST API:

``` text
network-anomaly-rest-api
```

Resource and method:

``` text
GET /network-traffic
```

Stage:

``` text
prod
```

The deployed API base URL recorded for this project is:

``` text
https://cyym8ywtvj.execute-api.ap-southeast-1.amazonaws.com/prod
```

Endpoint:

``` text
https://cyym8ywtvj.execute-api.ap-southeast-1.amazonaws.com/prod/network-traffic
```

Example test:

``` powershell
curl.exe -i "https://cyym8ywtvj.execute-api.ap-southeast-1.amazonaws.com/prod/network-traffic?limit=100"
```

The current API has no user authentication. Do not expose sensitive data
through this endpoint.

## 5. Frontend configuration and Amplify deployment

The frontend is located in:

``` text
frontend/
```

It is a React/Vite application. The API endpoint is supplied at build
time through:

``` text
VITE_API_URL
```

Set this variable in the Amplify app's environment variables to the full
API resource URL:

``` text
https://cyym8ywtvj.execute-api.ap-southeast-1.amazonaws.com/prod/network-traffic
```

Do not put credentials or secrets in `VITE_` variables. Vite exposes
these values to browser code.

Build locally:

``` powershell
cd "C:\Users\<YOUR_WINDOWS_USER>\Documents\Side Project\AWS-Network-Anomaly-Detection\frontend"

npm install
npm run build
```

The production build is written to `frontend/dist`.

The GitHub repository is:

``` text
https://github.com/bryanwork6099/AWS-Network-Anomaly-Detection
```

The production branch is `main`. Amplify is connected to the GitHub
repository and should start a deployment after a push when automatic
builds are enabled. Confirm the deployment status in the Amplify Console
rather than assuming the build succeeded.

## 6. Traffic test and end-to-end verification

From the project root, activate the project's virtual environment if one
is used, then publish test events.

Example suspicious traffic test:

``` powershell
python .\traffic-generator\publish_live_port_scan.py
```

The previously verified test generated 30 TCP events from
`192.168.1.210` to `10.0.5.10`, using 30 unique destination ports and
failed connection outcomes.

Allow the aggregation window to close and the scheduled finalizer/scorer
workflow to run. Then verify: - Kinesis consumer logs show records
processed. - DynamoDB contains the finalized aggregation window. -
Scorer Lambda logs show successful inference and record update. - The
DynamoDB record contains an anomaly score and classification. - API
Gateway returns HTTP 200 and includes the record. - The dashboard
displays the updated result.

Previously observed port-scan result:

  Field                                 Value
  -------------------------- ----------------
  Connections                              30
  Unique destination ports                 30
  Failed connections                       30
  Score                        `6.9276060125`
  Threshold                        `2.980612`
  Classification                    `ANOMALY`

Previously observed normal test:

  Field                        Value
  ---------------- -----------------
  Source IP          `192.168.1.250`
  Score               `0.7437485975`
  Threshold               `2.980612`
  Classification            `NORMAL`

These values are historical test observations, not guaranteed outputs
for every subsequent run.

## 7. GitHub update workflow

From the repository root:

``` powershell
git status
git add README.md DEPLOYMENT.md EXPLANATION.md screenshots/
git commit -m "Add project documentation and screenshots"
git push origin main
```

If Git reports there is nothing to commit, inspect `git status` and
confirm the documentation files and screenshots are in the repository
root and the expected folder.

## 8. Operational and cost notes

-   Review AWS Billing and Cost Management while resources remain
    deployed.
-   SageMaker endpoints, training jobs, Kinesis, DynamoDB, Lambda
    invocations, CloudWatch logs, S3 storage, and data transfer may
    incur charges.
-   The SageMaker endpoint is serverless but is not necessarily free.
-   Before stopping or deleting resources, identify dependencies and
    preserve model artifacts, logs, and evidence needed for the
    portfolio.
-   Do not disable deletion protection or delete production resources
    without first confirming the impact.

## 9. Security checklist

-   Use least-privilege IAM roles.
-   Keep AWS credentials out of Git.
-   Keep `.env.local`, virtual environments, `node_modules`, build
    output, and deployment ZIPs out of source control unless
    deliberately required.
-   Treat the API URL as public configuration, not a secret.
-   Add API authentication before exposing sensitive data.
-   Restrict CORS origins where appropriate.
-   Avoid publishing sensitive IP addresses, account identifiers, or log
    contents in screenshots.
