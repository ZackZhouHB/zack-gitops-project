pipeline {
    agent any
    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'jenkins',
                    credentialsId: 'gittoken',
                    url: 'https://github.com/ZackZhouHB/zack-gitops-project.git'
            }
        }
        //stage('SonarQube analysis') {
        //    steps {
        //        script {
        //           scannerHome = tool 'sonarscanner'
        //        }
        //        withSonarQubeEnv('SonarCloud') {
        //            withCredentials([string(credentialsId: 'sonar', variable: 'SONAR_TOKEN')]) {
        //                // If you have sonar-project.properties file in your repo
        //                //sh "${scannerHome}/bin/sonar-scanner"
        //                
        //                // Or if passing properties inline
        //                 sh "${scannerHome}/bin/sonar-scanner -Dsonar.login=${SONAR_TOKEN} -Dsonar.projectKey=jenkins-sonar -Dsonar.sources=. -Dsonar.organization=zack2ci-org"
        //            }
        //        }
        //    }
        //}
        stage('Check Docker') {
            steps {
                sh 'docker --version'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    // Specify the folder path where the Dockerfile is located
                    dockerImage = docker.build("zackz001/jenkins:${env.BUILD_NUMBER}", "zack_blog/")
                }
            }
        }
        stage('Push Docker Image to DockerHub') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', "${dockerhub}") {
                        dockerImage.push("${env.BUILD_NUMBER}")
                        dockerImage.push("latest") // Optionally tag as 'latest'
                    }
                }
            }
        }
    }
    post {
        success {
            echo "Docker image successfully built and pushed to DockerHub."
        }
        failure {
            echo "Build or push failed."
        } 
    }
}
