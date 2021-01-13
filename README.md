# 60k_tps_kinesis_demo
Demonstration of a simple multi-threaded producer (generator) and Kinesis setup parameters to show how Kinesis scales up to 500 shards.

# Summary
I built this quick demonstration (can setup from scratch in about 15 min, 5-10 min to demo) as a challenge to demonstrate Kinesis's ability to scale to large volumes within my account's 500 shard limit.  The dataset is a nested version of the TPC-DS store_sales subject area that could represent retail transactions being captured in real time.

# Setup

You will need an EC2 instance to run the driver Python script that will submit data to the Kinesis stream.  I used an m4.16xlarge running Amazon Linux 2.  The requirement.txt file is available for additional python libraries.

Next create a Kinesis stream called "store_sales" with 500 shards (or less).  If you want to demonstrate Firehose's capabilities, create a Firehose delivery stream that uses a bucket of your choice and prefix.

Firehose S3 Delivery Example:
```
Prefix:         tpcds/streaming/store_sales/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
Error Prefix:   tpcds/streaming/store_sales_error/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/!{firehose:error-output-type}/
```

If you deliver to Redshift instead of S3 use these parameters and the JSON path definition in the store_sales_jsonpath.json you've placed in a S3 bucket accessible from Kinesis Firehose:
```
DDL for Redshift Table (run this in Redshift):
DROP TABLE tpcds.streaming_store_sales;
CREATE TABLE tpcds.streaming_store_sales (
ss_addr_sk INTEGER
,ss_cdemo_sk INTEGER
,ss_coupon_amt FLOAT
,ss_customer VARCHAR(4096)
,ss_customer_address VARCHAR(4096)
,ss_customer_demographics VARCHAR(4096)
,ss_customer_sk INTEGER
,ss_date_dim VARCHAR(4096)
,ss_ext_discount_amt FLOAT
,ss_ext_list_price FLOAT
,ss_ext_sales_price FLOAT
,ss_ext_tax FLOAT
,ss_ext_wholesale_cost FLOAT
,ss_hdemo_sk INTEGER
,ss_household_demographics VARCHAR(4096)
,ss_item VARCHAR(4096)
,ss_item_sk INTEGER
,ss_list_price FLOAT
,ss_net_paid FLOAT
,ss_net_paid_inc_tax FLOAT
,ss_net_profit FLOAT
,ss_promo_sk INTEGER
,ss_promotion VARCHAR(4096)
,ss_quantity FLOAT
,ss_sales_price FLOAT
,ss_sold_time_sk INTEGER
,ss_store VARCHAR(4096)
,ss_store_sk INTEGER
,ss_ticket_number FLOAT
,ss_time_dim VARCHAR(4096)
,ss_wholesale_cost FLOAT
);

Firehose Delivery Params:
Temp Prefix: tpcds/streaming/store_sales_inter/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
ColumnList:ss_addr_sk,ss_cdemo_sk,ss_coupon_amt,ss_customer,ss_customer_address,ss_customer_demographics,ss_customer_sk,ss_date_dim,ss_ext_discount_amt,ss_ext_list_price,ss_ext_sales_price,ss_ext_tax,ss_ext_wholesale_cost,ss_hdemo_sk,ss_household_demographics,ss_item,ss_item_sk,ss_list_price,ss_net_paid,ss_net_paid_inc_tax,ss_net_profit,ss_promo_sk,ss_promotion,ss_quantity,ss_sales_price,ss_sold_time_sk,ss_store,ss_store_sk,ss_ticket_number,ss_time_dim,ss_wholesale_cost

COPY tpcds.streaming_store_sales (ss_addr_sk,ss_cdemo_sk,ss_coupon_amt,ss_customer,ss_customer_address,ss_customer_demographics,ss_customer_sk,ss_date_dim,ss_ext_discount_amt,ss_ext_list_price,ss_ext_sales_price,ss_ext_tax,ss_ext_wholesale_cost,ss_hdemo_sk,ss_household_demographics,ss_item,ss_item_sk,ss_list_price,ss_net_paid,ss_net_paid_inc_tax,ss_net_profit,ss_promo_sk,ss_promotion,ss_quantity,ss_sales_price,ss_sold_time_sk,ss_store,ss_store_sk,ss_ticket_number,ss_time_dim,ss_wholesale_cost) 
FROM 's3://jwyant-nestedblog/tpcds/streaming/store_sales_inter/2019/10/02/18/'
CREDENTIALS 'aws_iam_role=arn:aws:iam::123456789012:role/mySole' json 's3://jwyant-nestedblog/tpcds/store_sales_jsonpath.json';
```

If you want to use Amazon Athena to demo querying directly on the data you've landed in S3, use the ddl.sql file to generate a schema-on-read for the datasets in your delivery bucket/prefix you created earlier.  Make sure you change the bucket/prefix to your location.

You can run the MSCK TABLE REPAIR if you have existing data (I clear it each run) or manually create partitions (faster for demos than MSCK TABLE REPAIR).

Tweak the code for your actual landing location in S3 and partition keys:
```
ALTER TABLE orders ADD PARTITION (year = '2019', month = '09', day = '25') LOCATION 's3://jwyant-nestedblog/tpcds/streaming/store_sales/year=2019/month=09/day=25/'
```

I have also included a AWS Lambda consumer for loading into Amazon DynamoDB (a fully-managed NoSQL key-value and document database that delivers single-digit millisecond performance at any scale) and a simple GET script to demonstrate streaming into DynamoDB and retreiving objects.  Use the lambda_kinesis_to_dynamodb.py script as an event trigger for Kinesis, and run the GET script from the EC2 instance you created earlier or even your desktop (with the right IAM permissions).  The input parameters are ss_ticket_number and ss_item_sk.
