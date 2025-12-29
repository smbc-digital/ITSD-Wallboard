import boto3
import json
import os
from datetime import datetime, timedelta

def lambda_handler(event, context):
    print("Received event:", event)
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': 'CORS preflight response'})
        }
    
    try:
        # Get parameters from queryStringParameters or fallback to defaults
        query_params = event.get('queryStringParameters') or {}
        print("QueryParams (raw):", query_params)
        
        # Try to get StartHoursAgo and handle potential empty string
        start_hours_ago_str = query_params.get("StartHoursAgo", "24")
        print("StartHoursAgo (raw):", start_hours_ago_str)
        
        # Convert to int, handling empty string
        try:
            start_hours_ago = int(start_hours_ago_str) if start_hours_ago_str else 24
        except ValueError:
            print(f"Invalid StartHoursAgo value: '{start_hours_ago_str}'. Using default of 24.")
            start_hours_ago = 24
        
        print("StartHoursAgo (processed):", start_hours_ago)

        # Get required parameters from environment variables
        instance_id = os.environ.get('ConnectInstanceId')
        # queue_arn = os.environ.get('QueueArn')

        queue_arns_str = os.environ.get('QueueArns')
        
        if not instance_id:
            raise ValueError("ConnectInstanceId environment variable is required")
        
        if not queue_arns_str:
            raise ValueError("QueueArn environment variable is required")
            
        # Extract queue ID from ARN
        queues = extract_queue_ids_from_arns(queue_arns_str)
        if not queues:
            raise ValueError("Could not extract queue IDs from QueueArns")            

        # Extract instance ARN from queue ARN
        instance_arn = extract_instance_arn_from_queue_arn(queue_arns_str.split(',')[0].strip())
        if not instance_arn:
            raise ValueError("Could not extract instance ARN from QueueArn")
        
        print("Instance ID:", instance_id)
        print("Instance ARN:", instance_arn)
        print("Queue IDs:", queues)

        connect = boto3.client('connect')

        # Get the current metric data
        current_metric_data = connect.get_current_metric_data(
            InstanceId=instance_id,
            Filters={
                'Queues': queues
            },
            CurrentMetrics=[
                {
                    'Name': 'CONTACTS_IN_QUEUE',
                    'Unit': 'COUNT'
                },
                {
                    'Name': 'OLDEST_CONTACT_AGE',
                    'Unit': 'SECONDS'
                },
                {
                    'Name': 'AGENTS_ONLINE',
                    'Unit': 'COUNT'
                },
                {
                    'Name': 'AGENTS_ON_CALL',
                    'Unit': 'COUNT'
                },
                {
                    'Name': 'AGENTS_ON_CONTACT',
                    'Unit': 'COUNT'
                }
            ],
        )

        # Extract the desired metrics
        print("Current metric data:", current_metric_data)

        calls_in_queue = safe_get_metric_value(current_metric_data, 0)
        longest_wait_time = safe_get_metric_value(current_metric_data, 1)
        agents_online = safe_get_metric_value(current_metric_data, 2)
        agents_on_call = safe_get_metric_value(current_metric_data, 3)
        agents_on_contact = safe_get_metric_value(current_metric_data, 4)

                # Get the historical metric data
        start_time = datetime.now() - timedelta(hours=start_hours_ago)
        end_time = datetime.now()
        print("Start time:", start_time)
        print("End time:", end_time)

        historical_metric_data = connect.get_metric_data_v2(
            ResourceArn=instance_arn,  # Use the instance ARN, not queue ARN
            StartTime=start_time,
            EndTime=end_time,
            Filters=[
                {
                    'FilterKey': 'QUEUE',
                    'FilterValues': queues
                }
            ],
            Metrics=[
                {
                    'Name': 'CONTACTS_HANDLED'
                },
                {
                    'Name': 'CONTACTS_ABANDONED'
                },
                {
                    'Name': 'AVG_CONTACT_DURATION'
                },
                {
                    'Name': 'AGENT_ANSWER_RATE'
                }
            ]
        )

        # Extract the desired metrics
        print("Historical metric data:", historical_metric_data)
        calls_handled = safe_get_metric_value(historical_metric_data, 0)
        calls_abandoned = safe_get_metric_value(historical_metric_data, 1)
        avg_contact_duration = safe_get_metric_value(historical_metric_data, 2)
        agent_answer_rate = safe_get_metric_value(historical_metric_data, 3)

                # Passthrough custom information
        custom_information = os.environ.get('WallboardMessage', 'No custom information available.')

        # Get the agent statuses
        agent_statuses = []
        users = []
        try:
            response = connect.get_current_user_data(
                InstanceId=instance_id,
                Filters={
                    'Queues': queues
                },
                MaxResults=100
            )

            print("Current User Data:", response)
            
            for userData in response.get("UserDataList", []):
                user = userData.get("User", {})
                userResponse = connect.describe_user(
                    InstanceId=instance_id,
                    UserId=user.get("Id", "")
                )

                userStatus = userData.get("Status", {}).get("StatusName")
                users.append({
                    "Arn": user.get("Arn", ""),
                    "Id": user.get("Id", ""),
                    "OnContacts": len(user.get("Contacts", [])) > 0,
                    "Status": userStatus,
                    "FirstName": userResponse.get("User", {}).get("IdentityInfo").get("FirstName", ""),
                    "LastName": userResponse.get("User", {}).get("IdentityInfo").get("LastName", "")
                })
                
                if userStatus:
                    agent_statuses.append(userStatus)
                    
        except Exception as e:
            print(f"Error getting agent statuses: {str(e)}")
            # Continue without agent statuses rather than failing completely

                  # Prepare the response
        wallboard_data = {
            "CallsHandled": calls_handled,
            "CallsInQueue": calls_in_queue,
            "CallsAbandoned": calls_abandoned,
            "LongestWaitTime": longest_wait_time,
            "AgentStatuses": agent_statuses,
            "Users": users,
            "AgentAnswerRate": agent_answer_rate,
            "AverageContactDuration": avg_contact_duration,
            "CustomInformation": custom_information,
            "NumberOfAgents": len(agent_statuses),
            "StartHoursAgo": start_hours_ago_str,
            "AgentsOnline": agents_online,
            "AgentsOnCall": agents_on_call,
            "AgentsOnContact": agents_on_contact
        }

        print(f"Returning Data: {wallboard_data}")

        # Return the response with CORS headers
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(wallboard_data)
        }  
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Important: Include CORS headers in error responses too
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({"error": f"An internal server error occurred: {str(e)}"})
        }

def safe_get_metric_value(metric_data, index):
    try:
        return metric_data['MetricResults'][0]['Collections'][index]['Value']
    except (IndexError, KeyError):
        return 0

def get_cors_headers():
    """Return standard CORS headers"""
    return {
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Credentials': 'false'
    }

def extract_queue_ids_from_arns(queue_arns_str):
    """Extract queue IDs from comma-delimited ARN list"""
    if not queue_arns_str:
        return []
    
    queue_ids = []
    arns = queue_arns_str.split(',')
    
    for arn in arns:
        arn = arn.strip()
        if arn:
            queue_id = extract_queue_id_from_arn(arn)
            if queue_id:
                queue_ids.append(queue_id)
            else:
                print(f"Warning: Could not extract queue ID from ARN: {arn}")
    
    return queue_ids

def extract_queue_id_from_arn(queue_arn):
    """Extract queue ID from a single queue ARN"""
    if queue_arn:
        # ARN format: arn:aws:connect:region:account:instance/instance-id/queue/queue-id
        return queue_arn.split('/')[-1]
    return None

def extract_instance_arn_from_queue_arn(queue_arn):
    """Extract instance ARN from queue ARN"""
    if queue_arn:
        # Queue ARN: arn:aws:connect:region:account:instance/instance-id/queue/queue-id
        # Instance ARN: arn:aws:connect:region:account:instance/instance-id
        parts = queue_arn.split('/queue/')
        if len(parts) > 0:
            return parts[0]  # This gives us the instance ARN
    return None

def extract_instance_arn_from_queue_arn(queue_arn):
    """Extract instance ARN from queue ARN"""
    if queue_arn:
        # Queue ARN: arn:aws:connect:region:account:instance/instance-id/queue/queue-id
        # Instance ARN: arn:aws:connect:region:account:instance/instance-id
        parts = queue_arn.split('/queue/')
        if len(parts) > 0:
            return parts[0]  # This gives us the instance ARN
    return None