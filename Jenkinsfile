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
                    // Run the Ansible playbook on localhost
                    sh '''
                        ansible-playbook -i /etc/ansible/hosts /etc/ansible/test-playbook.yml
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
        stage('Terraform Init') {
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

        stage('Extract EC2 Public IP') {
            steps {
                script {
                    def ec2Ip = sh(script: 'terraform output -raw ec2_public_ip', returnStdout: true).trim()
                    echo "EC2 Public IP: ${ec2Ip}"
                    env.EC2_PUBLIC_IP = ec2Ip
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

