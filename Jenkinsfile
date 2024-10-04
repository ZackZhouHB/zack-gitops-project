pipeline {
    agent any
    environment {
        //REGISTRY_URL = 'https://index.docker.io/v1/'
        IMAGE_NAME = "zackz001/jenkins"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        LATEST_TAG = "latest"
        //TRIVY_OUTPUT = "trivy-report.txt"
        EMAIL_RECIPIENT = "zhbsoftboy1@gmail.com"
        GIT_REPO_URL = 'https://github.com/ZackZhouHB/zack-gitops-project.git'  // Git repository URL
        GIT_BRANCH = 'editing'  // Git branch
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub' // Docker Hub credentials
        REGION = 'ap-southeast-2'  // AWS region
        //SONAR_TOKEN = 'sonar'  // Fetch Sonar token securely
        //SNYK_INSTALLATION = 'snyk' // Replace with your Snyk installation
        //SNYK_TOKEN = 'snyktoken'  // Fetch Snyk token securely
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
        stage('Verify Ansible Installation') {
            steps {
                script {
                    try {
                        // Check if Ansible is accessible in the Jenkins container
                        sh '''
                            if command -v ansible >/dev/null 2>&1; then
                                echo "Ansible Version: $(ansible --version)"
                            else
                                echo "Ansible is not installed or not found"
                                exit 1
                            fi
                        '''
                    } catch (Exception e) {
                        echo "Error: Ansible not found. ${e.message}"
                    }
                }
            }
        }
        stage('Run Ansible Playbook') {
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
                }
            }
        }
        stage('Check AWS CLI Version') {
            steps {
                script {
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
        stage('hello AWS') {
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

        stage('Wait for EC2 and Docker to be Ready') {
            steps {
                script {
                    // Extract EC2 Public IP
                    def ec2Ip = sh(script: 'terraform output -raw ec2_public_ip', returnStdout: true).trim()
                    env.EC2_PUBLIC_IP = ec2Ip
                    echo "EC2 Public IP: ${env.EC2_PUBLIC_IP}"

                    // Wait until EC2 instance is up and Docker is ready
                    def maxRetries = 30 // Maximum retries (adjust as needed)
                    def interval = 30 // Interval between retries in seconds

                    def isReady = false
                    for (int i = 0; i < maxRetries; i++) {
                        try {
                            // Check if the web service is accessible on port 80
                            def response = sh(script: "curl -s -o /dev/null -w '%{http_code}' http://${env.EC2_PUBLIC_IP}:80", returnStdout: true).trim()
                            if (response == '200') {
                                echo "EC2 instance and Docker container are ready! Web service is accessible."
                                isReady = true
                                break
                            } else {
                                echo "Waiting for EC2 and Docker to be ready... (Attempt: ${i + 1}/${maxRetries})"
                            }
                        } catch (Exception e) {
                            echo "Failed to connect. Retrying in ${interval} seconds..."
                        }
                        sleep(interval)
                    }

                    if (!isReady) {
                        error "EC2 instance or Docker container did not become ready in time."
                    }
                }
            }
        }

        stage('Test SSH Connection') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'sshkey', keyFileVariable: 'SSH_KEY')]) {
                    script {
                        // Test SSH connection to the EC2 instance
                        def sshCommand = "ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ec2-user@${env.EC2_PUBLIC_IP} 'echo SSH connection successful!'"
                        def sshSuccess = false
                        retry(5) { // Retry 5 times in case SSH is not immediately ready
                            try {
                                sh sshCommand
                                sshSuccess = true
                            } catch (Exception e) {
                                echo "SSH connection failed. Retrying..."
                                sleep(10)
                            }
                        }

                        if (!sshSuccess) {
                            error "Failed to establish SSH connection after retries."
                        } else {
                            echo "SSH connection to EC2 instance successful!"
                        }
                    }
                }
            }
        }
//        stage('Install Docker and Run Image on EC2') {
//            steps {
//                script {
//                    withCredentials([sshUserPrivateKey(credentialsId: 'your-ssh-key-id', keyFileVariable: 'SSH_KEY')]) {
//                        sh '''
//                            ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ubuntu@${EC2_PUBLIC_IP} << EOF
//                            sudo apt-get update
//                            sudo apt-get install -y docker.io
//                            sudo systemctl start docker
//                            sudo docker pull zackz001/jenkins:${BUILD_NUMBER}
//                            sudo docker run -d -p 8080:8080 zackz001/jenkins:${BUILD_NUMBER}
//                            EOF
//                        '''
//                    }
//                }
//            }
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

