#!/usr/bin/env python

import boto3
import snappy
import json
import sys
import pprint
import base64
from itertools import chain, islice
from multiprocessing.pool import ThreadPool
from contextlib import closing

def get_matching_s3_prefixes(bucket, prefix='', delimiter='/'):
    """
    Generate the common prefixes in an S3 bucket.

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch keys that start with this prefix (optional).
    :param delimiter: use this delimter for "folders" (optional).
    """
    s3 = boto3.client('s3')
    kwargs = {'Bucket': bucket, 'Delimiter': delimiter}

    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    while True:
        resp = s3.list_objects_v2(**kwargs)
        for common_prefix in resp['CommonPrefixes']:
            prefix = common_prefix['Prefix']
            yield prefix
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break

def get_matching_s3_keys(bucket, prefix='', suffix=''):
    """
    Generate the keys in an S3 bucket.

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch keys that start with this prefix (optional).
    :param suffix: Only fetch keys that end with this suffix (optional).
    """
    s3 = boto3.client('s3')
    kwargs = {'Bucket': bucket}

    # If the prefix is a single string (not a tuple of strings), we can
    # do the filtering directly in the S3 API.
    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    while True:

        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp['Contents']:
            key = obj['Key']
            if key.startswith(prefix) and key.endswith(suffix):
                yield key

        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (when this field is missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break

def stream_s3_snappy_object_line_by_line_generator(bucket, key):
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket='jwyant-nestedblog', Key=key)
    body = obj['Body']
    with closing(body):
        decompressor = snappy.hadoop_snappy.StreamDecompressor()
        last_line = ''
        try:
            while True:
                chunk = last_line+decompressor.decompress(next(body)).decode("utf-8")
                chunk_by_line = chunk.split('\n')
                last_line = chunk_by_line.pop()
                for line in chunk_by_line:
                    yield line
        except StopIteration:
            yield last_line
            return

def stream_data_from_key(current_key):
    if current_key.endswith('.snappy'):
        s3 = boto3.client('s3')
        mysnappystream = stream_s3_snappy_object_line_by_line_generator(bucket='jwyant-nestedblog', key=current_key)
        i = 0
        records = []
        while True:
            try:
                rec = next(mysnappystream)
            except StopIteration:
                break
        #for rec in mysnappystream:
            try:
                rec_dict = json.loads(rec)
            except json.decoder.JSONDecodeError:
                continue
            record = dict(
                Data=rec,
                PartitionKey=str(rec_dict['ss_ticket_number'])
            )
            records.append(record)
            i += 1
            if i%100 == 0:
                #print(len(records))
                kinesis_client = boto3.client('kinesis')
                response = kinesis_client.put_records(Records=records, StreamName='store_sales')
                records = []
        return True
    else:
        return False

def main(workers=1, offset = 0):
    ss_sold_date_sk_partition_generator = get_matching_s3_prefixes(bucket='jwyant-nestedblog', prefix='tpcds/json/store_sales/ss_sold_date_sk=')
    while True:
        try:
            current_partition = next(ss_sold_date_sk_partition_generator)
        except StopIteration:
            break
        print(current_partition)
        ss_keys_generator = get_matching_s3_keys(bucket='jwyant-nestedblog', prefix=current_partition)
        ss_keys_list_full = list(ss_keys_generator)
        ss_keys_list_tobeworked = ss_keys_list_full[workers*offset:workers*(offset+1)]
        pool = ThreadPool(workers)
        pool.map(stream_data_from_key, ss_keys_list_tobeworked)
        pool.close()

if __name__ == "__main__":
    workers = int(sys.argv[1])
    offset = int(sys.argv[2])
    main(workers = workers, offset = offset)
