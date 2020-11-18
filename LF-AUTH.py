import json
import boto3
from botocore.vendored import requests
import time
import random


def lambda_handler(event, context):
    print("connected auth")
    name = event['name']
    number = event['number']

    collectionId = 'Collection'
    frame_name = "frame.jpg"

    rekognition = rekognition = boto3.client('rekognition')
    rekognition_index_response = rekognition.index_faces(CollectionId=collectionId, Image={
        'S3Object': {'Bucket': 'unauthorized-xinchi', 'Name': frame_name}},
                                                         ExternalImageId=frame_name,
                                                         MaxFaces=1,
                                                         QualityFilter="AUTO",
                                                         DetectionAttributes=['ALL'])
    print(rekognition_index_response)
    #     return {
    #     'statusCode': 500,
    #     'body': 'Internal Server Error'
    # }

    faceId = ''
    for faceRecord in rekognition_index_response['FaceRecords']:
        faceId = faceRecord['Face']['FaceId']

    print(faceId)

    dynamo_client = boto3.resource('dynamodb')
    visitor_table = dynamo_client.Table('visitors-wyh')

    rekognition_bucket = "photo-collection-xinchi"
    photos = []
    photo_dict = {}
    object_key = str(faceId) + "." + str(name) + ".jpg"
    bucket = rekognition_bucket
    createdTimeStamp = int(time.time())
    photo_dict["objectKey"] = object_key
    photo_dict["bucket"] = bucket
    photo_dict["createdTimeStamp"] = createdTimeStamp

    photos.append(photo_dict)

    visitor_table.put_item(
        Item={
            "faceID": faceId,
            "visitorName": name,
            "phoneNumber": number,
            "photos": photos
        }
    )
    print("visitor stored")
    s3 = boto3.resource('s3')
    copy_source = {
        'Bucket': 'unauthorized-xinchi',
        'Key': frame_name
    }
    known_visitors_bucket = s3.Bucket('photo-collection-xinchi')
    known_visitors_bucket.copy(
        copy_source, object_key
    )

    print("copy success")
    otp = generate_otp(faceId, int(time.time() + 300))
    print("otp success")
    send_sns(otp, number)
    print("success")
    delete_table('unauthorized-xinchi')
    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }


def generate_otp(faceId, expirationTime):
    dynamo_client = boto3.resource('dynamodb')
    otp_table = dynamo_client.Table('passcodes-wyh')

    otp = ""
    for i in range(6):
        otp += str(random.randint(1, 9))

    otp_table.put_item(
        Item={
            "access_code": otp,
            "faceID": faceId,
            "ttl": int(expirationTime)}
    )

    return otp


def send_sns(otp, number):
    sns = boto3.client('sns', region_name='us-east-1')
    print(type(number))
    print(number)
    message = "Your One Time Password is " + str(
        otp) + " Enter it in this link.  " + "http://wp1-xinchi.s3-website-us-east-1.amazonaws.com"
    response = sns.publish(PhoneNumber="+1" + number, Message=message)
    return response


def delete_table(tablename):
    dynamo_client = boto3.resource('dynamodb')
    table = dynamo_client.Table(tablename)
    scan = table.scan()
    print(scan)
    for i in scan['Items']:
        table.delete_item(
            Key=i
        )