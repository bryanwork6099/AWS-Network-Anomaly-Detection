# AWS Network Anomaly Detection

## 1. Project Overview

AWS Network Anomaly Detection is a cloud-based network traffic monitoring and anomaly detection platform built using AWS managed services and machine learning.

The project collects network traffic events, processes and aggregates them in near real time, and uses an Amazon SageMaker Random Cut Forest (RCF) model to identify potentially suspicious network activity.

Detected anomalies are stored in Amazon DynamoDB and made available through an API Gateway endpoint. A React-based Security Operations Center (SOC)-style dashboard provides visibility into network traffic, anomaly classifications, and detection results.

**Project objectives:**
- Build an end-to-end cloud-native network monitoring pipeline.
- Process streaming network traffic using AWS services.
- Apply machine learning to identify unusual network activity.
- Store and retrieve network analysis results.
- Present security insights through a web-based dashboard.
- Demonstrate practical AWS cloud engineering, networking, and security skills.

## 2. Architecture Overview

### High-Level Architecture

Traffic Generator → Amazon Kinesis Data Streams → AWS Lambda Consumer → Amazon DynamoDB → EventBridge Scheduler → Window Finalizer → DynamoDB Streams → Anomaly Scorer Lambda → Amazon SageMaker Random Cut Forest → Amazon DynamoDB → API Gateway → React SOC Dashboard

### Architecture Components

| Component | AWS Service | Responsibility |
|---|---|---|
| Traffic generation | Python | Generates network traffic events for testing |
| Streaming ingestion | Amazon Kinesis Data Streams | Receives streaming traffic events |
| Stream processing | AWS Lambda | Processes incoming traffic records |
| Data aggregation | Amazon DynamoDB | Stores and aggregates traffic windows |
| Scheduled processing | Amazon EventBridge Scheduler | Triggers window finalization |
| Window finalization | AWS Lambda | Finalizes expired traffic aggregation windows |
| Change detection | DynamoDB Streams | Detects newly finalized records |
| Anomaly scoring | AWS Lambda | Prepares features and invokes the ML endpoint |
| Machine learning | Amazon SageMaker Random Cut Forest | Generates anomaly scores |
| Data access | Amazon API Gateway | Exposes network analysis results |
| Frontend hosting | AWS Amplify | Hosts the React dashboard |

## 3. Network Traffic Ingestion

A Python-based traffic generator publishes network traffic events to Amazon Kinesis Data Streams.

The generated events contain network-related attributes such as:
- Source IP address
- Destination IP address
- Destination port
- Network protocol
- Connection status
- Bytes sent and received
- Event timestamp
- Unique event identifier

The Kinesis stream receives these records for downstream processing.

**Kinesis configuration:**
- Stream: `network-traffic-stream-v3`
- Region: `ap-southeast-1`
- Capacity mode: On-demand
- Retention period: 24 hours
- Shards: 4

## 4. Stream Processing and Data Aggregation

An AWS Lambda consumer processes incoming Kinesis records.

The consumer:
1. Reads records from Kinesis Data Streams.
2. Decodes the incoming event data.
3. Validates and processes traffic attributes.
4. Aggregates traffic information into time-based windows.
5. Stores aggregation records in Amazon DynamoDB.
6. Uses event identifiers to prevent duplicate processing.

The aggregation process calculates metrics including:
- Total connections
- Unique destination IP addresses
- Unique destination ports
- TCP and UDP connections
- Failed connections
- Bytes sent and received

### DynamoDB

Table: `network-anomaly-aggregation-v3`

The table stores traffic aggregation records and processing metadata.

A Global Secondary Index named `GSI1-OpenWindowsByFinalizeAt` supports efficient retrieval of aggregation windows that are ready for finalization.

The table also uses Time to Live (TTL) for expiring eligible records.

## 5. Scheduled Window Finalization

Amazon EventBridge Scheduler invokes the window finalizer Lambda function every minute.

The finalizer:
1. Queries eligible open aggregation windows.
2. Identifies windows that have reached their finalization time.
3. Updates their status to `FINALIZED`.
4. Removes temporary GSI attributes used for open-window tracking.

Finalized records become eligible for downstream anomaly scoring.

## 6. Machine Learning Anomaly Detection

### Amazon SageMaker Random Cut Forest

The project uses Amazon SageMaker's built-in Random Cut Forest algorithm for anomaly detection.

Random Cut Forest is an unsupervised learning algorithm that identifies unusual observations based on their deviation from learned data patterns.

Unlike a traditional supervised classifier, it does not require manually labelled examples for training.

### Model Configuration

| Parameter | Configuration |
|---|---|
| Algorithm | Random Cut Forest |
| Feature dimension | 10 |
| Number of trees | 100 |
| Samples per tree | 256 |
| Instance type for training | `ml.m5.large` |
| Model version | `rcf-v3` |
| Endpoint | `network-anomaly-rcf-v3-serverless-endpoint` |
| Endpoint memory | 2048 MB |
| Maximum concurrency | 1 |

### Feature Engineering

The model uses 10 numerical features:

1. `total_connections`
2. `unique_destination_ips`
3. `unique_destination_ports`
4. `log_bytes_sent`
5. `log_bytes_received`
6. `failed_connection_rate`
7. `destination_ip_ratio`
8. `destination_port_ratio`
9. `udp_ratio`
10. `log_failed_connections`

The same feature transformation logic is applied during model inference to maintain consistency between training and production scoring.

### Anomaly Scoring

The anomaly scorer Lambda function is triggered through DynamoDB Streams when finalized records are created or updated.

It:
1. Receives finalized aggregation records.
2. Extracts and transforms the required features.
3. Invokes the SageMaker endpoint.
4. Retrieves the anomaly score.
5. Compares the score against the configured threshold.
6. Updates the DynamoDB record with the detection result.

**Detection threshold:** `2.980612`

Classification logic:

- Score above threshold: `ANOMALY`
- Score at or below threshold: `NORMAL`

The threshold is configurable through the scorer Lambda environment variable `ANOMALY_THRESHOLD`.

## 7. API Layer

Amazon API Gateway exposes the network analysis records through a REST API.

**API endpoint:**

`GET /network-traffic`

Example:

`https://cyym8ywtvj.execute-api.ap-southeast-1.amazonaws.com/prod/network-traffic?limit=100`

The API Lambda function retrieves finalized records from DynamoDB and returns JSON responses.

It supports:
- Retrieving recent network traffic records.
- Limiting the number of returned records.
- Filtering records by source IP address.

The API is integrated with the React frontend using the `VITE_API_URL` environment variable.

## 8. SOC Dashboard

The frontend is built using React and Vite and hosted through AWS Amplify.

The dashboard provides a centralized interface for viewing network monitoring and anomaly detection results.

### Dashboard capabilities

- SOC-inspired dashboard interface.
- Network traffic metrics.
- Anomaly detection statistics.
- Network event records.
- Anomaly classification visibility.
- Automatic API data refresh.
- API error and data status handling.

The frontend retrieves data from API Gateway without directly accessing DynamoDB or SageMaker.

### Deployment

The frontend source code is maintained in GitHub and connected to AWS Amplify for deployment.

GitHub repository:

https://github.com/bryanwork6099/AWS-Network-Anomaly-Detection

Production deployment uses the `main` branch.

## 9. Testing and Validation

The project was tested using both normal and suspicious network traffic scenarios.

### Normal Traffic Test

A normal traffic event was published and processed through the complete pipeline.

Observed result:

| Attribute | Result |
|---|---|
| Source IP | `192.168.1.250` |
| Anomaly score | `0.7437485975` |
| Threshold | `2.980612` |
| Classification | `NORMAL` |

The score was below the configured anomaly threshold.

### Suspicious Port Scan Test

A simulated port scan was generated to test the detection pipeline.

Test characteristics:
- Source IP: `192.168.1.210`
- Destination IP: `10.0.5.10`
- 30 network events
- 30 unique destination ports
- TCP connection failures

Observed result:

| Attribute | Result |
|---|---|
| Total connections | 30 |
| Unique destination ports | 30 |
| Failed connections | 30 |
| Anomaly score | `6.9276060125` |
| Threshold | `2.980612` |
| Classification | `ANOMALY` |

The anomaly score exceeded the configured threshold and the event window was classified as anomalous.

### Additional Validation

The following were also tested:
- Kinesis record processing.
- Duplicate event handling.
- DynamoDB aggregation.
- Scheduled window finalization.
- SageMaker endpoint invocation.
- DynamoDB Streams event processing.
- Normal and anomalous traffic scoring.
- API Gateway HTTP response.
- Frontend API integration.
- Frontend production build.
- GitHub source code deployment.

## 10. Security Considerations

Security considerations for this implementation include:

- AWS IAM roles and policies for service-to-service access.
- Restricted permissions for Lambda functions.
- Separation of data processing, inference, and API responsibilities.
- DynamoDB deletion protection.
- Environment variables for application configuration.
- Git ignore rules to prevent local environment files and credentials from being committed.

**Important production improvement:** The current API endpoint does not have user authentication. A production deployment should introduce an appropriate authentication and authorization mechanism, alongside tighter CORS configuration and API access controls.

## 11. Cost Considerations

The architecture uses managed AWS services to reduce operational overhead.

Cost-sensitive design decisions include:
- On-demand Kinesis capacity.
- DynamoDB on-demand billing.
- SageMaker Serverless Inference.
- No provisioned SageMaker endpoint concurrency.
- Lambda-based processing.
- Time-based record expiration using DynamoDB TTL.

AWS resources may still incur charges while deployed. Review the AWS Billing and Cost Management console and shut down or remove resources when they are no longer required.

## 12. Current Limitations and Future Improvements

The current implementation demonstrates an end-to-end anomaly detection pipeline, but it can be extended further.

Potential improvements include:

1. Add authentication to API Gateway.
2. Introduce role-based dashboard access.
3. Implement fully functional multi-page dashboard navigation.
4. Add real-time dashboard updates using WebSockets.
5. Integrate Amazon GuardDuty findings.
6. Add Amazon SNS alerts for high-priority anomalies.
7. Improve model evaluation using additional representative traffic datasets.
8. Implement model retraining and version management.
9. Add CloudWatch dashboards and operational alarms.
10. Improve API pagination and query efficiency for larger datasets.

## 13. Conclusion

This project demonstrates the design and implementation of a cloud-native network anomaly detection platform using AWS managed services and machine learning.

It combines network traffic ingestion, event-driven processing, data aggregation, machine learning inference, REST API development, and frontend deployment into a single end-to-end architecture.

The project provides practical experience in AWS networking, serverless computing, streaming data processing, DynamoDB, SageMaker, IAM, API Gateway, and cloud security engineering.

**Technologies:** Python, React, Vite, AWS Lambda, Amazon Kinesis Data Streams, Amazon DynamoDB, Amazon EventBridge Scheduler, Amazon SageMaker, Amazon API Gateway, AWS Amplify, Git, and GitHub.
