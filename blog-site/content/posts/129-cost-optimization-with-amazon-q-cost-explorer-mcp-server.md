---
title: "Cost Optimization with Amazon Q & Cost Explorer MCP Server"
date: 2025-04-20T08:36:56Z
slug: cost-optimization-with-amazon-q-cost-explorer-mcp-server
categories: ["AWS"]
aliases: ["/post/129/"]
legacy_id: 129
---
Managing cloud costs effectively, especially on AWS, is crucial. Wasted resources can easily inflate bills. This post introduces the **AWS Cost Explorer MCP Server**, a tool designed to simplify analyzing your AWS spending using the Model Context Protocol (MCP).

**GitHub Repository:** <https://github.com/awslabs/mcp/tree/main/src/cost-explorer-mcp-server>

[![[Image Placeholder 01: Introduction Graphic]](/images/mcp1.png)](/images/mcp1.png)

**What this AWS Cost Explorer MCP Server Does**

This specific MCP Server, provided by AWS Labs, acts as a specialized tool that connects an AI assistant like Amazon Q directly to the detailed AWS cost and usage data. Think of it as giving us AI assistant the specific knowledge and tools needed to understand and analyze our cloud spending.

Leveraging this server through an AI like Amazon Q offers significant advantages over manually navigating the AWS Cost Explorer console or writing complex API queries:

- **Deeper, Actionable Cost Insights:** Go beyond standard console reports. The server allows the AI to break down costs granularly (by service, region, tag, etc.) and identify specific drivers of spending changes.
- **Conversational Cost Querying:** Ask complex cost questions in plain English directly within your chat interface (like Amazon Q). For example, query "Why did my S3 costs increase last Tuesday?" or "Which EC2 instances in the 'dev' environment are costing the most?" without needing specialized query languages.
- **Automated, Context-Aware Optimization:** This is a key benefit. The server can analyze your Infrastructure as Code (IaC) definitions and current resource usage patterns to provide tailored optimization suggestions. It might recommend switching specific instances to Reserved Instances, identify idle resources, or suggest downsizing opportunities, directly within your AI chat.
- **Real-time Pricing Checks:** The server enables the AI to fetch current AWS pricing information on demand, helping validate costs or explore pricing for different configurations.

In essence, this MCP server transforms how engineers interact with AWS cost data, making analysis more intuitive, proactive, and integrated into their workflow when paired with an AI assistant like Amazon Q.

**Quick Start: How to Install and Run AWS Cost Explorer MCP Server**

**Prerequisites**

- Install uv, Python, AWSCli
- Configure AWS credentials with permissions to access AWS services. Ensure you have:
  - An AWS account with appropriate permissions.
  - AWS credentials configured using aws configure or environment variables.
  - Your IAM role or user must have permission to access the AWS Pricing API.
- Install AmazonQ
- Create AWS Builder ID and sign in using AWS Builder ID in AmazonQ

**Installation Steps**

1. **Install AWS CLI:** <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
2. **Install Amazon Q:**<https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html#command-line-installing-appimage>- **Register an AWS Builder ID.**

     [![[Image Placeholder: Amazon Q Login Screen]](/images/mcp4.png)](/images/mcp4.png)
   - **Login AmazonQ using the AWS Builder ID.**

     [![[Image Placeholder: Amazon Q Login Screen]](/images/mcp2.png)](/images/mcp2.png)
   - **Set up MCP server Configuration File:**
     Create a file at local AmazonQ folder with the following content, so we can work with MCP across AWS using defined MCP server and interact with AWS account profiles, like here I defined my own AWS profile "zack", The MCP Server will use the AWS profile specified in the AWS\_PROFILE environment variable. If this variable is not set, it defaults to the "default" profile in our AWS configuration, Ensure the AWS profile used has permissions to access the AWS Pricing API.

     ```bash
     vim ~/.aws/amazonq/mcp.json
     {
       "mcpServers": {
         "awslabs.cost-analysis-mcp-server": {
           "command": "uvx",
           "args": ["awslabs.cost-explorer-mcp-server@latest"],
           "env": {
             "FASTMCP_LOG_LEVEL": "ERROR",
             "AWS_PROFILE": "zack"
           },
           "disabled": false,
           "autoApprove": []
         },
         "awslabs.aws-pricing-mcp-server": {
           "command": "uvx",
           "args": [
             "awslabs.aws-pricing-mcp-server@latest"
           ],
           "env": {
             "AWS_PROFILE": "zack",
             "FASTMCP_LOG_LEVEL": "ERROR"
           }
         },
         "awslabs.cdk-mcp-server": {
           "command": "uvx",
           "args": [
             "awslabs.cdk-mcp-server@latest"
           ],
           "env": {
             "FASTMCP_LOG_LEVEL": "ERROR"
           }
         },
         "awslabs.aws-documentation-mcp-server": {
           "command": "uvx",
           "args": [
             "awslabs.aws-documentation-mcp-server@latest"
           ],
           "env": {
             "FASTMCP_LOG_LEVEL": "ERROR"
           },
           "disabled": false,
           "autoApprove": []
         },
         "awslabs.terraform-mcp-server": {
           "command": "uvx",
           "args": [
             "awslabs.terraform-mcp-server@latest"
           ],
           "env": {
             "FASTMCP_LOG_LEVEL": "ERROR"
           },
           "disabled": false,
           "autoApprove": []
         }
       }
     }
     ```

   - **Complete Installation and Start Chatting:**

     The MCP Server uses the specified profile to create a boto3 session for authenticating with AWS services. So our AWS IAM credentials remain local and are only used to access AWS services.

     Start the chat interface:

     ```text
     >q chat
     >help me analyze last 2 months spending
     ```

     **Output Example:**

     [![[Image Placeholder: 'q chat' command in terminal]](/images/mcp0.png)](/images/mcp0.png)

     [![[Image Placeholder: 'q chat' command in terminal]](/images/mcp3.png)](/images/mcp3.png)

**Summary**

The **AAWS Cost Explorer MCP Server** provides enterprises with an efficient and intelligent solution for cost analysis. Through the standardized MCP protocol, we can easily integrate cost analysis capabilities, enhancing our ability to manage cloud service costs effectively via AI powered AmazonQ and MCP server.

Think of **Amazon Q direct** as having a helpful assistant who can look up your basic spending information and trends from Cost Explorer and explain them.

Think of **Amazon Q + MCP Server** as giving that assistant access to a specialized financial analyst tool (the MCP server). This tool can perform much deeper dives, connect different data points (like pricing details or infrastructure definitions), generate formal reports, and provide concrete advice on how to save money.

The key difference lies in **the depth of analysis, report generation, and actionable optimization suggestions** provided by the dedicated AWS Cost Explorer MCP Server, which goes beyond the built-in capabilities of Amazon Q alone.

More AWS Labs MCP servers to be explored:

- **AWS Bedrock Knowledge Base Retrieval MCP server:**
  <https://github.com/awslabs/mcp/tree/main/src/bedrock-kb-retrieval-mcp-server>
- **AWS Terraform MCP server:**
  <https://github.com/awslabs/mcp/tree/main/src/terraform-mcp-server>
