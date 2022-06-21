## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0
from importlib.metadata import metadata
import json
import boto3
import logging
from botocore.exceptions import ClientError

from schema.aws.securityhub.securityhubfindingsimported import Marshaller
from schema.aws.securityhub.securityhubfindingsimported import AWSEvent


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

secHubClient = boto3.client('securityhub')


def lambda_handler(event, context):
    status_code = 200
    message ='function complete'

    #Deserialize event into strongly typed object
    aws_event:AWSEvent = Marshaller.unmarshall(event, AWSEvent)
    suppression_text = "Supressed Finding"
    suppression_author = "Security Hub - Suppression Automation"
    suppression_finding_id = ""
    suppression_finding_arn = ""
    #log the event
    logger.debug(aws_event)
    finding = aws_event.detail.findings[0]
    #store this Finding's ID, ARN and Account ID
    suppression_finding_id = finding["Id"]
    suppression_finding_arn = finding["ProductArn"]
    user_defined_fields = {}
    if finding['UserDefinedFields'] :
        user_defined_fields = finding['UserDefinedFields']
    logger.debug("Finding ID: %s " , suppression_finding_id + " and product arn " + suppression_finding_arn)
    try:
        #add the note to the finding and add a userDefinedField to use in the event bridge rule and prevent repeat lookups
        response = secHubClient.batch_update_findings(
            FindingIdentifiers=[
                {
                    'Id': suppression_finding_id,
                    'ProductArn': suppression_finding_arn
                }
            ],
            Severity={"Label": "INFORMATIONAL"},
            Workflow={"Status": "SUPPRESSED"},
            Note={
                'Text': suppression_text,
                'UpdatedBy': suppression_author
            },
            UserDefinedFields=user_defined_fields
        )
    except ClientError as error:
        logger.warn(error.response['Error']['Message'])
        status_code = 500
        message = error.response['Error']['Message']
    except Exception as error:
        status_code = 500
        message = "Unexpected Error occured"
    else:
        if response["UnprocessedFindings"]:
            status_code = 500
            message = 'Failed to update finding'
            logger.warning("Failed to update finding %s", response["UnprocessedFindings"])
        else:
            logger.info("successfully posted note to finding: %s" , suppression_finding_id + "API response: " + str(response))
    return {
        'statusCode': status_code,
        'body': json.dumps(message)
    }
