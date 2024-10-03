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
    }

    stages {
        stage('SonarQube analysis') {
        steps {
            script {
                scannerHome = tool 'sonarscanner'// must match the name of an actual scanner installation directory on your Jenkins build agent
            }
            withSonarQubeEnv('SonarCloud') {
            sh "${scannerHome}/bin/sonar-scanner"
            }
        }
        }
    }
}