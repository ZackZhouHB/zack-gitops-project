pipeline {
    agent any
    environment {
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub'
        SONAR_TOKEN = 'sonar'
    }
    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'jenkins',
                    credentialsId: 'gittoken',
                    url: 'https://github.com/ZackZhouHB/zack-gitops-project.git'
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
                    dockerImage = docker.build("zackz001/jenkins:${env.BUILD_NUMBER}", "zack_blog/")
                }
            }
        }
        stage('Docker Image Scan') {
            steps {
                // Use Trivy to scan the built Docker image
                sh "trivy image --severity HIGH,CRITICAL zackz001/jenkins:${env.BUILD_NUMBER} > trivy-report.txt"
            }
        }
        stage('Push Docker Image to DockerHub') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', "${DOCKERHUB_CREDENTIALS_ID}") {
                        dockerImage.push("${env.BUILD_NUMBER}")
                        dockerImage.push("latest") // Optionally push the image as 'latest'
                    }
                }
            }
        }
        stage('Display Trivy Scan Results') {
            steps {
                script {
                    // Display the contents of the trivy-report.txt file
                    def scanReport = readFile('trivy-report.txt')
                    echo "Trivy Scan Report:\n${scanReport}"
                }
            }
        }
    }
    post {
        success {
            echo "Docker image successfully built, scanned, and pushed to DockerHub."
        }
        failure {
            echo "Build, scan, or push failed."
        } 
    }
}
