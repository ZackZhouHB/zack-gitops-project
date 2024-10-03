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
        stage('SonarQube analysis') {
            steps {
                script {
                    scannerHome = tool 'sonarscanner'
                }
                withSonarQubeEnv('SonarCloud') {
                    withCredentials([string(credentialsId: 'sonar', variable: 'SONAR_TOKEN')]) {
                        // If you have sonar-project.properties file in your repo
                        //sh "${scannerHome}/bin/sonar-scanner"
                        
                        // Or if passing properties inline
                         sh "${scannerHome}/bin/sonar-scanner -Dsonar.login=${SONAR_TOKEN} -Dsonar.projectKey=jenkins-sonar -Dsonar.sources=. -Dsonar.organization=zack2ci-org"
                    }
                }
            }
        }
    }
}
