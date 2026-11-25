# Architecture and Technical Explanation

This document explains how the AWS Network Anomaly Detection project
works, why each component exists, and how an event moves through the
system.

## 1. What the system does

The application accepts generated network telemetry, groups related
events into short time windows, derives numerical traffic features, and
asks a machine-learning model to score each completed window.

The score is compared with a configured threshold: - `ANOMALY` when
score \> `2.980612` - `NORMAL` when score \<= `2.980612`

The scored records are stored in DynamoDB and served to a React
dashboard through API Gateway.

This is a portfolio-scale anomaly-scoring pipeline using generated test
traffic. It is not a packet inspection appliance, firewall, SIEM, or a
validated production intrusion detection service.

## 2. Architecture diagram

``` mermaid
flowchart TB
    subgraph INGEST["1. Ingestion and aggregation"]
        A["Python traffic generator"] --> B["Amazon Kinesis Data Streams"]
        B --> C["Lambda: Kinesis consumer"]
        C --> D[("DynamoDB aggregation table")]
    end

    subgraph FINALIZE["2. Window finalization"]
        E["EventBridge Scheduler<br/>every minute"] --> F["Lambda: window finalizer"]
        F --> D
    end

    subgraph DETECT["3. Anomaly detection"]
        D --> G["DynamoDB Streams"]
        G --> H["Lambda: anomaly scorer"]
        H --> I["SageMaker Random Cut Forest endpoint"]
        I --> H
        H --> D
    end

    subgraph PRESENT["4. API and presentation"]
        D --> J["Lambda: API"]
        J --> K["API Gateway REST API"]
        K <--> L["React dashboard on AWS Amplify"]
    end
```

## 3. Stage 1 - Traffic generation and ingestion

### Python traffic generator

The traffic generator creates network event records for testing. The
events represent network connection activity and include fields such
as: - Source IP address - Destination IP address - Destination port -
Protocol - Connection result - Bytes sent and received - Timestamp -
Unique event ID

The project includes a simulated port-scan publisher used to create a
recognizable suspicious pattern for validation.

### Amazon Kinesis Data Streams

Kinesis is the streaming ingestion layer. It decouples event generation
from downstream processing: the producer publishes records, and the
consumer reads them asynchronously.

The configured stream is `network-traffic-stream-v3` in
`ap-southeast-1`, using on-demand capacity and 24-hour retention.

## 4. Stage 2 - Stream processing and aggregation

### Kinesis consumer Lambda

The consumer Lambda is connected to the Kinesis stream through an event
source mapping. It reads batches of records, decodes the event payloads,
and updates aggregation state.

The consumer groups events into time-based windows, so the model scores
a summary of activity rather than each individual event independently.

It also uses unique event identifiers and deduplication records. This is
important because stream processing can deliver records more than once;
idempotent processing prevents a replay from inflating traffic counts.

### DynamoDB aggregation table

The table `network-anomaly-aggregation-v3` stores window records and
related processing metadata.

The aggregation includes measures such as: - Total connections - Unique
destination IP addresses - Unique destination ports - TCP and UDP
connection counts - Failed connection count - Bytes sent and received

The GSI `GSI1-OpenWindowsByFinalizeAt` indexes open windows by their
finalization time. This lets the finalizer locate windows that are due
without scanning every item in the table.

## 5. Stage 3 - Window finalization

A window should not be scored while events are still being added to it.
The project therefore uses a scheduled finalization stage.

### EventBridge Scheduler

The schedule `network-anomaly-window-finalizer-schedule` invokes the
finalizer every minute.

### Window finalizer Lambda

The finalizer queries eligible open windows through the GSI. For each
due window, it: 1. Checks that the window is ready to close. 2. Marks
the record `FINALIZED`. 3. Removes the temporary GSI attributes used to
find open windows.

Finalization creates a stable aggregation snapshot for inference.
Updating the DynamoDB item also produces a DynamoDB Streams record.

## 6. Stage 4 - Machine-learning anomaly scoring

### DynamoDB Streams

DynamoDB Streams captures item changes. The scorer Lambda is connected
to the stream and reacts to relevant finalized records.

The stream was configured with `NEW_AND_OLD_IMAGES`. The scorer's event
source mapping was configured with batch size 1 and starting position
`LATEST`.

### Anomaly scorer Lambda

The scorer Lambda: 1. Reads the changed DynamoDB record. 2. Determines
whether it is a finalized aggregation that needs scoring. 3. Extracts
the aggregation metrics. 4. Applies the feature transformations expected
by the model. 5. Invokes the SageMaker endpoint. 6. Receives the anomaly
score. 7. Compares the score with the configured threshold. 8. Writes
the score, classification, and model version back to DynamoDB.

The feature transformation used for inference must match the training
feature order and transformation. A mismatch could produce meaningless
model scores even if the endpoint invocation succeeds.

### Random Cut Forest

Random Cut Forest is an unsupervised anomaly detection algorithm. It
uses random partitioning of the feature space to estimate how unusual an
observation is relative to the patterns represented by the model.

The project uses ten features:

  -----------------------------------------------------------------------
  Feature                             What it represents
  ----------------------------------- -----------------------------------
  `total_connections`                 Number of connections in the window

  `unique_destination_ips`            Number of distinct destination IPs

  `unique_destination_ports`          Number of distinct destination
                                      ports

  `log_bytes_sent`                    Log-transformed bytes sent

  `log_bytes_received`                Log-transformed bytes received

  `failed_connection_rate`            Proportion of failed connections

  `destination_ip_ratio`              Derived destination-IP diversity
                                      measure

  `destination_port_ratio`            Derived destination-port diversity
                                      measure

  `udp_ratio`                         Proportion of UDP connections

  `log_failed_connections`            Log-transformed failed connection
                                      count
  -----------------------------------------------------------------------

The deployed model uses 100 trees, 256 samples per tree, and a feature
dimension of 10. The SageMaker endpoint uses Serverless Inference with
2048 MB memory and maximum concurrency of 1.

### Score threshold

The project uses `2.980612` as the classification threshold. The scorer
labels a record as anomalous when the returned score is above that
threshold.

The threshold is a project configuration derived during model
validation. It should be re-evaluated when the training data, feature
engineering, model, or traffic distribution changes. A score is an
anomaly indicator, not a statement that malicious activity has been
conclusively proven.

## 7. Stage 5 - Storage, API, and dashboard

### Scored result in DynamoDB

The scorer writes its results back to the aggregation record. The stored
result includes the anomaly score, classification, and model version
alongside the aggregated traffic attributes.

### API Lambda and API Gateway

The API Lambda reads finalized records from DynamoDB and formats them as
JSON. API Gateway exposes the Lambda through the `GET /network-traffic`
resource.

The API supports a result limit and source-IP filtering. The current
global retrieval path uses a bounded DynamoDB Scan with a filter, so it
is appropriate for the current project size but is not a substitute for
a query-optimized, paginated production API.

### AWS Amplify and React

AWS Amplify hosts the built React/Vite frontend. The browser application
requests data from API Gateway using the `VITE_API_URL` build-time
setting.

The frontend is a presentation and investigation interface. It does not
invoke SageMaker or query DynamoDB directly.

## 8. End-to-end example: simulated port scan

The project's port-scan test generated 30 TCP connection events: -
Source: `192.168.1.210` - Destination: `10.0.5.10` - 30 unique
destination ports - 30 failed connections

The events were published to Kinesis, processed by the consumer, and
accumulated into a time window. The finalizer closed the window. The
scorer transformed its metrics and invoked SageMaker.

The previously observed result was:

  Metric                       Observed value
  -------------------------- ----------------
  Total connections                        30
  Unique destination ports                 30
  Failed connections                       30
  Anomaly score                `6.9276060125`
  Threshold                        `2.980612`
  Classification                    `ANOMALY`

The score exceeded the threshold, so the scorer stored the record as
`ANOMALY`. The API then made the finalized record available to the
dashboard.

For comparison, a previously tested normal sample from `192.168.1.250`
returned score `0.7437485975`, below the threshold, and was classified
as `NORMAL`.

These are specific test observations, not a guarantee that every port
scan or every normal event will be classified correctly.

## 9. Reliability and operational considerations

-   **Duplicate delivery:** The consumer uses event IDs and
    deduplication state to avoid counting the same event more than once.
-   **Window boundaries:** The finalizer separates event aggregation
    from model inference so the model scores a completed time window.
-   **Stream processing:** Lambda event source mappings and DynamoDB
    Streams are asynchronous. Monitor retries, iterator age, errors, and
    throttling.
-   **Inference dependency:** Scoring depends on the SageMaker endpoint
    being available and the feature payload matching the model input
    format.
-   **API scale:** The current bounded Scan approach is a small-project
    implementation. A production API should use query patterns supported
    by appropriate indexes and pagination.
-   **Observability:** Use CloudWatch Logs and metrics to trace
    ingestion, finalization, scoring, and API errors.

## 10. Security boundaries and limitations

The project uses IAM roles for AWS service access. Each role should be
scoped to only the required resources and actions.

The API currently has no user authentication. CORS is not an
authentication mechanism. Before production use, add an authorizer,
restrict access, review CORS origins, protect sensitive logs, and define
data-retention and backup policies.

The traffic generator creates simulated telemetry. The current system
does not capture packets from a live network interface, inspect payload
contents, or automatically block traffic. It produces anomaly scores
from aggregated event metadata; a human or downstream security workflow
would need to investigate and respond to alerts.

## 11. Possible extensions

-   Ingest telemetry from real network sensors or flow logs.
-   Add authentication and role-based access to the dashboard.
-   Add notifications for high-priority anomalies.
-   Add query indexes and API pagination.
-   Add CloudWatch alarms and operational dashboards.
-   Add model evaluation against broader labelled test datasets.
-   Add retraining, model versioning, and threshold review workflows.
-   Provision the infrastructure through AWS CDK, CloudFormation, or
    Terraform.
