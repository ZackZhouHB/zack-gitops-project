###############################################################################
# Bedrock Knowledge Base + Data Sources
# - OpenSearch Serverless collection already exists (created via CLI)
# - Collection name: platform-health-kb, id: 0s43wsj0nu6nsj4bdlxf
###############################################################################

# --- OpenSearch data-access policy (grants Bedrock KB role + deployer) ------

resource "aws_opensearchserverless_access_policy" "bedrock_kb" {
  name = "${var.project_name}-kb-access"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/platform-health-kb/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/platform-health-kb"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# --- Vector index in OpenSearch Serverless -----------------------------------
# The Bedrock KB requires a vector index to exist before it can store embeddings.
# We create it via the OpenSearch API using a null_resource + local-exec.
# NOTE: The collection must be ACTIVE and the access policy above must be
#       applied before the index can be created.

resource "null_resource" "opensearch_vector_index" {
  triggers = {
    collection_id = "0s43wsj0nu6nsj4bdlxf"
    index_name    = "bedrock-knowledge-base-default-index"
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -e

      COLLECTION_ENDPOINT=$(aws opensearchserverless batch-get-collection \
        --ids "${self.triggers.collection_id}" \
        --query 'collectionDetails[0].collectionEndpoint' \
        --output text \
        --region ${var.aws_region} \
        --profile ${var.aws_profile})

      # Check if index already exists (ignore errors – 404 means not found)
      STATUS=$(curl -s -o /dev/null -w "%%{http_code}" \
        --aws-sigv4 "aws:amz:${var.aws_region}:aoss" \
        --user "" \
        "$COLLECTION_ENDPOINT/${self.triggers.index_name}" 2>/dev/null || true)

      if [ "$STATUS" = "200" ]; then
        echo "Index ${self.triggers.index_name} already exists – skipping creation."
        exit 0
      fi

      echo "Creating vector index ${self.triggers.index_name} ..."
      curl -s -X PUT \
        --aws-sigv4 "aws:amz:${var.aws_region}:aoss" \
        --user "" \
        -H "Content-Type: application/json" \
        "$COLLECTION_ENDPOINT/${self.triggers.index_name}" \
        -d '{
          "settings": {
            "index": {
              "knn": true,
              "knn.algo_param.ef_search": 512
            }
          },
          "mappings": {
            "properties": {
              "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                  "engine": "faiss",
                  "name": "hnsw",
                  "parameters": {
                    "m": 16,
                    "ef_construction": 512
                  },
                  "space_type": "l2"
                }
              },
              "AMAZON_BEDROCK_METADATA": {
                "type": "text",
                "index": false
              },
              "AMAZON_BEDROCK_TEXT_CHUNK": {
                "type": "text"
              }
            }
          }
        }'

      echo ""
      echo "Vector index created successfully."
    EOT
  }

  depends_on = [aws_opensearchserverless_access_policy.bedrock_kb]
}

# --- Bedrock Knowledge Base --------------------------------------------------

resource "aws_bedrockagent_knowledge_base" "main" {
  name     = "${var.project_name}-kb"
  role_arn = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_embed_model_id}"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = var.opensearch_collection_arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_access_policy.bedrock_kb,
    null_resource.opensearch_vector_index,
  ]
}

# --- Data Source 1: S3 (PDF documents) --------------------------------------

resource "aws_bedrockagent_data_source" "s3" {
  name                 = "s3-documents"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.kb_documents.arn
      inclusion_prefixes = ["documents/"]
    }
  }
}

# --- Data Source 2: Web Crawler (blog) ---------------------------------------

resource "aws_bedrockagent_data_source" "web_crawler" {
  name                 = "blog-crawler"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "WEB"
    web_configuration {
      source_configuration {
        url_configuration {
          seed_urls {
            url = var.blog_url
          }
        }
      }
      crawler_configuration {
        crawler_limits {
          rate_limit = 10
        }
        scope = "HOST_ONLY"
      }
    }
  }
}

# --- Data Source 3: Confluence -----------------------------------------------

resource "aws_bedrockagent_data_source" "confluence" {
  name                 = "confluence-pages"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "CONFLUENCE"
    confluence_configuration {
      source_configuration {
        host_url               = var.confluence_host
        host_type              = "SAAS"
        auth_type              = "BASIC"
        credentials_secret_arn = aws_secretsmanager_secret.confluence_token.arn
      }
      crawler_configuration {
        filter_configuration {
          type = "PATTERN"
          pattern_object_filter {
            filters {
              object_type       = "Page"
              inclusion_filters = [".*ET.*"]
            }
          }
        }
      }
    }
  }
}

# --- Outputs -----------------------------------------------------------------

output "bedrock_knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}

output "bedrock_s3_data_source_id" {
  value = aws_bedrockagent_data_source.s3.data_source_id
}

output "bedrock_web_data_source_id" {
  value = aws_bedrockagent_data_source.web_crawler.data_source_id
}

output "bedrock_confluence_data_source_id" {
  value = aws_bedrockagent_data_source.confluence.data_source_id
}
