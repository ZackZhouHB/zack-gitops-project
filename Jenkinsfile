pipeline {
    agent any
    environment {
        IMAGE_NAME = "zackz001/jenkins"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        LATEST_TAG = "latest"
        EMAIL_RECIPIENT = "zhbsoftboy1@gmail.com"
        GIT_REPO_URL = 'https://github.com/ZackZhouHB/zack-gitops-project.git'  // Git repository URL
        GIT_BRANCH = 'editing'  // Git branch
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub' // Docker Hub credentials
        REGION = 'ap-southeast-2'  // AWS region
    }
    stages {
        stage('Clean Workspace') {
            steps {
                cleanWs()
            }
        }
        stage('Checkout Code') {
            steps {
                git branch: "${GIT_BRANCH}",
                    credentialsId: 'gittoken',
                    url: "${GIT_REPO_URL}"
            }
        }
        stage('Check Installed Package Versions') {
            steps {
                script {
                    try {
                        // Check Docker version
                        sh '''
                            if command -v docker >/dev/null 2>&1; then
                                echo "Docker Version: $(docker --version)"
                            else
                                echo "Docker is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Docker not found. ${e.message}"
                    }

                    try {
                        // Check Terraform version
                        sh '''
                            if command -v terraform >/dev/null 2>&1; then
                                echo "Terraform Version: $(terraform -version)"
                            else
                                echo "Terraform is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Terraform not found. ${e.message}"
                    }

                    try {
                        // Check Kubectl version
                        sh '''
                            if command -v kubectl >/dev/null 2>&1; then
                                echo "Kubectl Version: $(kubectl version --client)"
                            else
                                echo "Kubectl is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Kubectl not found. ${e.message}"
                    }

                    try {
                        // Check Trivy version
                        sh '''
                            if command -v trivy >/dev/null 2>&1; then
                                echo "Trivy Version: $(trivy --version)"
                            else
                                echo "Trivy is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Trivy not found. ${e.message}"
                    }

                    try {
                        // Check Ansible version
                        sh '''
                            if command -v ansible >/dev/null 2>&1; then
                                echo "Ansible Version: $(ansible --version)"
                            else
                                echo "Ansible is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Ansible not found. ${e.message}"
                    }

                    try {
                        // Check AWS CLI version
                        sh '''
                            if command -v aws >/dev/null 2>&1; then
                                echo "AWS CLI Version: $(aws --version)"
                            else
                                echo "AWS CLI is not installed"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: AWS CLI not found. ${e.message}"
                    }
                }
            }
        }
        stage('Run a testing Ansible Playbook') {
            steps {
                script {
                    // Run the Ansible playbook using the hosts file from the repo
                    sh '''
                        echo "Running Ansible playbook:"
                        ansible-playbook -i "${WORKSPACE}/jenkins/terraform/hosts" "${WORKSPACE}/jenkins/terraform/test-playbook.yaml"
                    '''
                }
            }
        }
        stage('Verify AWS credential') {
            steps {
                withAWS(credentials: 'aws', region: 'ap-southeast-2') { // Replace with correct AWS credentials ID
                    script {
                        // List all existing S3 buckets and output the result to the Jenkins console
                        sh '''
                            echo "Listing all S3 buckets:"
                            aws s3 ls
                        '''
                    }
                }
            }
        }
        stage('Terraform Init and Apply') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws']]) {
                    sh '''
                        export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                        export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                        cd jenkins/terraform
                        terraform init
                        terraform apply -auto-approve -var "aws_region=${REGION}"
                    '''
                }
            }
        }
        // Stage to extract EC2 public IP
        stage('Extract EC2 Public IP') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws']]) {
                    script {
                        def ec2Ip = sh(script: '''
                            cd jenkins/terraform
                            terraform output -raw ec2_public_ip
                        ''', returnStdout: true).trim()
                        echo "EC2 Public IP: ${ec2Ip}"
                        // Set the environment variable for the next stages explicitly
                        env.EC2_PUBLIC_IP = ec2Ip
                    }
                }
            }
        }

        // **Fix: Adding a small sleep to ensure env is populated**
        stage('Validate EC2 Public IP') {
            steps {
                script {
                    sleep 5 // Ensure enough time for variable propagation
                    if (env.EC2_PUBLIC_IP == null || env.EC2_PUBLIC_IP == "") {
                        error "EC2 Public IP is not available or failed to fetch."
                    } else {
                        echo "EC2 Public IP is successfully fetched: ${env.EC2_PUBLIC_IP}"
                    }
                }
            }
        }

        // Wait for EC2 Readiness (SSH Validation)
        stage('Wait for EC2 Readiness') {
            steps {
                retry(4) { // Retry up to 4 times in case EC2 is not immediately ready
                    sleep 15  // Wait for a bit before checking readiness
                    withCredentials([sshUserPrivateKey(credentialsId: 'sshkey', keyFileVariable: 'SSH_KEY')]) {
                        script {
                            sh "ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ubuntu@${env.EC2_PUBLIC_IP} 'echo EC2 is ready for deployment'"
                        }
                    }
                }
            }
        }

        // Deploy Docker using Ansible
        stage('Deploy Docker with Ansible') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'sshkey', keyFileVariable: 'SSH_KEY')]) {
                    script {
                        sh '''
                            echo "Running Ansible Playbook for Docker Deployment..."
                            ansible-playbook -i "${EC2_PUBLIC_IP}," "${WORKSPACE}/jenkins/terraform/deploy-docker-playbook.yml" \
                            --user ubuntu \
                            --private-key ${SSH_KEY} \
                            --extra-vars "ansible_ssh_private_key_file=${SSH_KEY} ec2_ip=${EC2_PUBLIC_IP}"
                        '''
                    }
                }
            }
        }
    }
    post {
        success {
            echo "Pipeline completed successfully."
        }
        failure {
            echo "Pipeline failed."
        }
    }
}
