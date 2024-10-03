// Define the detectJavaVersion function outside of the pipeline block
def detectJavaVersion() {
    def javaVersionOutput = sh(script: 'java -version 2>&1', returnStatus: false, returnStdout: true).trim()
    def javaVersionMatch = javaVersionOutput =~ /openjdk version "(\d+\.\d+)/

    if (javaVersionMatch) {
        def javaVersion = javaVersionMatch[0][1]

        if (javaVersion.startsWith("1.8")) {
            return '8'
        } else if (javaVersion.startsWith("11")) {
            return '11'
        } else if (javaVersion.startsWith("17")) {
            return '17'
        } else {
            error("Unsupported Java version detected: ${javaVersion}")
        }
    } else {
        error("Java version information not found in output.")
    }
}

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
        SNYK_INSTALLATION = 'snyk' // Replace with your Snyk installation
        SNYK_TOKEN = 'snyktoken'  // Fetch Snyk token securely
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
        stage('Detect and Set Java') {
            steps {
                script {
                    try {
                        def javaVersion = detectJavaVersion()  // Detect the Java version, e.g., "17"
                        def javaToolName = "Java_${javaVersion}"  // Expected tool name

                        // Try to set the Java version; fallback if the specific version isn't found
                        try {
                            tool name: javaToolName, type: 'jdk'
                            echo "Using Java version ${javaVersion}."
                        } catch (Exception toolError) {
                            echo "No JDK named ${javaToolName} found. Using default JDK."
                        }

                        // Verify Java version, regardless of whether the specific version was found
                        sh 'java --version'

                    } catch (Exception e) {
                        echo "Error during Java version detection: ${e.message}"
                        // Continue pipeline even if Java detection fails
                    }
                }
            }
        }
        stage('snyk_analysis') {
            steps {
                script {
                    echo 'Testing...'
                    try {
                        snykSecurity(
                            snykInstallation: SNYK_INSTALLATION,
                            snykTokenId: SNYK_TOKEN,
                            failOnIssues: false,
                            monitorProjectOnBuild: true,
                            additionalArguments: '--all-projects --d'
                        )
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        pipelineError = true
                        error("Error during snyk_analysis: ${e.message}")
                    }
                }
            }
        }        
        stage('Check and Build Docker Image') {
            steps {
                script {
                    try {
                        // Check if Docker is available
                        sh 'docker --version'
                        echo "Docker is installed. Proceeding to build the Docker image..."
                        
                        // Build the Docker image from the 'zack_blog' folder
                        dockerImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}", "zack_blog/")
                    } catch (Exception e) {
                        // Handle the error if Docker is not available
                        error("Docker is not installed or accessible. Cannot proceed with the build.")
                    }
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
