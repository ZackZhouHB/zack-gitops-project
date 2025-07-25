{
  "Comment": "HSC Results Processing Workflow",
  "StartAt": "ParseAndValidateCSV",
  "States": {
    "ParseAndValidateCSV": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${parser_lambda_arn}",
        "Payload.$": "$"
      },
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Next": "ProcessBatches",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "ProcessingFailed"
        }
      ]
    },
    "ProcessBatches": {
      "Type": "Map",
      "ItemsPath": "$.Payload.batches",
      "MaxConcurrency": 10,
      "Iterator": {
        "StartAt": "ProcessSingleBatch",
        "States": {
          "ProcessSingleBatch": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "${batch_processor_lambda_arn}",
              "Payload.$": "$"
            },
            "End": true
          }
        }
      },
      "Next": "ProcessingSucceeded"
    },
    "ProcessingFailed": {
      "Type": "Fail",
      "Comment": "Processing failed, check logs.",
      "Error": "CSVProcessingError",
      "Cause": "The CSV processing workflow failed."
    },
    "ProcessingSucceeded": {
      "Type": "Succeed"
    }
  }
}