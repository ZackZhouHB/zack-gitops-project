pipeline {
    agent any
    environment {
        SONAR_TOKEN = credentials('sonar') // Use Jenkins credentials
    }
    stages {
        stage('Checkout Code') {
            steps {
                git branch: 'jenkins',
                    credentialsId: 'gittoken',
                    url: 'https://github.com/ZackZhouHB/zack-gitops-project.git'
            }
        }
        stage('SonarQube analysis') {
            steps {
                script {
                    scannerHome = tool 'sonarscanner' // Must match the SonarScanner installation
                }
                withSonarQubeEnv('SonarCloud') {
                    sh "${scannerHome}/bin/sonar-scanner -Dsonar.login=${SONAR_TOKEN}"
                }
            }
        }
    }
}
