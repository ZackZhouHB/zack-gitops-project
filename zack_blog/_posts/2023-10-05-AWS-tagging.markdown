---
layout: post
title: Automate AWS EC2 tagging
date:   2023-10-01 11:15:29 +1100
categories: jekyll Cat2
---

<b> Backgroud </b>

I was tasked to enforce mandatory tagging for ec2 instances, as there are a lot of machines and a lot of tags need to be attached to each machine, here I need a scripted way to get the job done. 


<b> How to achieve </b>

- Prepare a list of ec2 instances with default name tag only,

![image tooltip here](/assets/awstag2.png)

- Open cloud shell or ssh to a linux box where AWSCli installed and configured to a AWS account, export the instances with ID to a csv file

{% highlight shell %}
root@ubt-server:~# aws ec2 describe-instances --output text --query 'Reservations[*].Instances[*].[InstanceId]' > zztag.csv
{% endhighlight %}

- Then add the header row for "instance ID" "tagA"  "valueA"    "tagB"  "valueB"

![image tooltip here](/assets/awstag1.png)

<b> Create shell script to read the CSV file line by line, and add tags for each instance </b>

{% highlight shell %}
root@ubt-server:~# vim zacktag.sh

#!/bin/bash

# Read the CSV file line by line
while IFS=, read -r instance_id tagA valueA tagB valueB || [ -n "$instance_id" ]; do
    # Add tagA
    aws ec2 create-tags --resources "$instance_id" --tags Key="$tagA",Value="$valueA"
    # Add tagB
    aws ec2 create-tags --resources "$instance_id" --tags Key="$tagB",Value="$valueB"
done < zztag.csv

root@ubt-server:~# chmod +x zacktag.sh && sh zacktag.sh
{% endhighlight %}

- Validate now ec2 instances with all tags attached
{% highlight shell %}
root@ubt-server:~# aws ec2 describe-tags --filters "Name=resource-id,Values=i-0980018fc6f4f722c"
{
    "Tags": [
        {
            "Key": "Name",
            "ResourceId": "i-0980018fc6f4f722c",
            "ResourceType": "instance",
            "Value": "testing-for-tagging"
        },
        {
            "Key": "zz1",
            "ResourceId": "i-0980018fc6f4f722c",
            "ResourceType": "instance",
            "Value": "aa5"
        },
        {
            "Key": "zz2",
            "ResourceId": "i-0980018fc6f4f722c",
            "ResourceType": "instance",
            "Value": "bb4"
        }
    ]
}
root@ubt-server:~# aws ec2 describe-tags --filters "Name=resource-id,Values=i-076226daa5aaf7cf2"
{
    "Tags": [
        {
            "Key": "Name",
            "ResourceId": "i-076226daa5aaf7cf2",
            "ResourceType": "instance",
            "Value": "zack-blog"
        },
        {
            "Key": "zz1",
            "ResourceId": "i-076226daa5aaf7cf2",
            "ResourceType": "instance",
            "Value": "aa1"
        },
        {
            "Key": "zz2",
            "ResourceId": "i-076226daa5aaf7cf2",
            "ResourceType": "instance",
            "Value": "aa2"
        }
    ]
}

{% endhighlight %}
![image tooltip here](/assets/awstag3.png)

- create cronjob to update tagging monthly

{% highlight shell %}
# create a monthly cron to run the script
root@ubt-server:~# crontab -e
no crontab for root - using an empty one

Select an editor.  To change later, run 'select-editor'.
  1. /bin/nano        <---- easiest
  2. /usr/bin/vim.basic
  3. /usr/bin/vim.tiny
  4. /bin/ed

Choose 1-4 [1]: 2
crontab: installing new crontab

# List the monthly scheduled cronjob
root@ubt-server:~# crontab -l
0 0 1 * * ~/zacktag.sh

{% endhighlight %}


<b> Conclusion </b>

Now we have a scripted way to achieve adding different tags for multiple ec2 instances via AWS CLI and shell script, same method to any other AWS resources that needed to be tagged, together with cronjob, we can only update the csv file which regularly updates resource ID and tags we want to attach, upload the csv file, every month their tags will be updated accordingly.

Furthermore, the resouces can be queried by setting up filter by different tag criteria:
{% highlight shell %}
# query EC2 with certain tag
aws ec2 describe-instances --filters "Name=tag:TagName,Values=TagValue"

# query EC2 without certain tag
aws ec2 describe-instances --query 'Reservations[].Instances[?not_null(Tags[?Key==`TagName` && Value==`TagValue`])].InstanceId'

{% endhighlight %}

Or we can use lambda function together with AWS Config rules to list and remediate the untagged EC2 resource accordingly
{% highlight shell %}
import boto3

def lambda_handler(event, context):
    # Initialize AWS clients for services to be scanned 
    ec2_client = boto3.client('ec2')
    
    # Retrieve a list of untagged EC2 instances
    untagged_instances = []
    response = ec2_client.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if 'Tags' not in instance:
                untagged_instances.append(instance['InstanceId'])
                
    return untagged_instances
{% endhighlight %}