pipeline {
    agent any
    environment {
        REGISTRY_URL = 'https://index.docker.io/v1/'
        IMAGE_NAME = "zackz001/jenkins"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        LATEST_TAG = "latest"
        TRIVY_OUTPUT = "trivy-report.txt"
        EMAIL_RECIPIENT = "zhbsoftboy1@gmail.com"
        GIT_REPO_URL = 'https://github.com/ZackZhouHB/zack-gitops-project.git'  // Git repository URL
        GIT_BRANCH = 'jenkins'  // Git branch
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub' // Docker Hub Cred
        SONAR_TOKEN = 'sonar'  // Fetch Sonar token securely
    }
    stages {
        stage('Checkout Code') {
            steps {
                git branch: "${GIT_BRANCH}",
                    credentialsId: 'gittoken',
                    url: "${GIT_REPO_URL}"
            }
        }
        stage('Check Docker') {
            steps {
                sh 'docker --version'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image from the 'zack_blog' folder
                    dockerImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}", "zack_blog/")
                }
            }
        }
        stage('Docker Image Scan') {
            steps {
                // Use Trivy to scan the built Docker image
                sh "trivy image --severity HIGH,CRITICAL ${IMAGE_NAME}:${IMAGE_TAG} > ${TRIVY_OUTPUT}"
            }
        }
        stage('Push Docker Image to DockerHub') {
            steps {
                script {
                    docker.withRegistry("${REGISTRY_URL}", "${DOCKERHUB_CREDENTIALS_ID}") {
                        dockerImage.push("${IMAGE_TAG}")
                        dockerImage.push("${LATEST_TAG}") // Push 'latest' tag
                    }
                }
            }
        }
        stage('Display Trivy Scan Results') {
            steps {
                script {
                    // Display the contents of the Trivy report
                    def scanReport = readFile("${TRIVY_OUTPUT}")
                    echo "Trivy Scan Report:\n${scanReport}"
                }
            }
        }
    }
    post {
        success {
            script {
                def scanReport = readFile("${TRIVY_OUTPUT}")
                emailext(
                    to: "${EMAIL_RECIPIENT}",
                    subject: "CI Pipeline Success: Build ${IMAGE_TAG}",
                    body: """
                    The pipeline has successfully completed.

                    Docker image ${IMAGE_NAME}:${IMAGE_TAG} has been built and pushed to DockerHub.

                    Trivy Scan Report:
                    ${scanReport}
                    """
                )
            }
        }
        failure {
            emailext(
                to: "${EMAIL_RECIPIENT}",
                subject: "CI Pipeline Failed: Build ${IMAGE_TAG}",
                body: """
                The pipeline has failed at some stage.

                Please check the Jenkins console logs for more details.
                """
            )
        }
    }
}
