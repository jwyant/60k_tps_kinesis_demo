#/usr/bin/bin python
import base64
import json
import boto3
import datetime
import decimal
import pprint
import sys


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

dynamodb = boto3.resource('dynamodb')
table = table = dynamodb.Table('store_sales')


try:
    start_datetime = datetime.datetime.now()
    response = table.get_item(
        Key={
            'ss_ticket_number': int(sys.argv[1]),
            'ss_item_sk': int(sys.argv[2])
        }
    )
    end_datetime = startdt = datetime.datetime.now()
except ClientError as e:
    print(e.response['Error']['Message'])
else:
    item = response['Item']
    print("GetItem succeeded:", end_datetime - start_datetime)
    print(json.dumps(item, indent=4, cls=DecimalEncoder))
