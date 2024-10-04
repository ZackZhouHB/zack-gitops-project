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
                        ansible-playbook --syntax-check -i /etc/ansible/hosts /etc/ansible/test-playbook.yml
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
                withAWS(credentials: 'aws', region: 'ap-southeast-2') {
                    sh 'echo "hello KB">hello.txt'
                    s3Upload acl: 'Private', bucket: 'kb-bucket', file: 'hello.txt'
                    s3Download bucket: 'kb-bucket', file: 'downloadedHello.txt', path: 'hello.txt'
                    sh 'cat downloadedHello.txt'
        // Other stages (e.g., build, scan, push) can go here
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
