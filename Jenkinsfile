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
}
