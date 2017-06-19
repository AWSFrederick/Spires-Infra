import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    cloudfront_id = 'E331D9A4QW76J0'
    client = boto3.client('cloudfront')
    if message['NewStateValue'] == 'ALARM':
        logger.info('Entering Maintaince Mode')
        cf_cfg = client.get_distribution_config(Id=cloudfront_id)
        cf_cfg['DistributionConfig']['DefaultRootObject'] = 'maint.html'
        response = client.update_distribution(DistributionConfig=cf_cfg['DistributionConfig'],
                                                 Id=cloudfront_id,
                                                 IfMatch=cf_cfg['ETag'])
        logger.info(response)
    else:
        logger.info('Leaving Maintaince Mode')
        cf_cfg = client.get_distribution_config(Id=cloudfront_id)
        cf_cfg['DistributionConfig']['DefaultRootObject'] = 'index.html'
        response = client.update_distribution(DistributionConfig=cf_cfg['DistributionConfig'],
                                                 Id=cloudfront_id,
                                                 IfMatch=cf_cfg['ETag'])
        logger.info(response)

    return 0
