---
layout: post
title:  "Jenkins - Universal CI Pipeline with Ansible & Terraform"
date:   2024-08-02 11:15:29 +1100
categories: jekyll Cat2
---

<b>Jenkins recap</b>

It has been some time since I adapted CI/CD pipelines from Jenkins to AWS CodePipeline and GitHub Actions workflows. Now, it's time to recap and improve some of my previous Jenkins practices.

- Universal Jenkins Docker image design

This time, instead of installing Jenkins on a server, I prefer to containerize a universal Jenkins Docker image with the necessary packages installed, so it provides consistency and reproducibility, portability, and easy updates and rollbacks. 

1. Docker CLI
2. Terraform
3. Kubectl
4. Trivy
5. AWS CLI
6. Ansible 

{% highlight shell %}
# Dockerfile

FROM jenkins/jenkins:lts

USER root

# Install necessary packages, Docker CLI, Terraform, Kubectl, Trivy, AWS CLI, and Ansible
RUN apt-get update && \
    apt-get install -y \
        curl \
        wget \
        unzip \
        gnupg2 \
        apt-transport-https \
        lsb-release \
        ca-certificates \
        software-properties-common \
        python3 \
        python3-venv \
        python3-pip && \

    # Install Docker CLI
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \

    # Install Terraform
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y terraform && \

    # Install Kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \

    # Install Trivy
    wget https://github.com/aquasecurity/trivy/releases/download/v0.56.0/trivy_0.56.0_Linux-64bit.deb && \
    dpkg -i trivy_0.56.0_Linux-64bit.deb && \
    rm trivy_0.56.0_Linux-64bit.deb && \

    # Install AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws/ && \

    # Create a virtual environment for Python and Ansible
    python3 -m venv /opt/ansible_venv && \
    /opt/ansible_venv/bin/pip install --upgrade pip && \
    /opt/ansible_venv/bin/pip install ansible && \

    # Create symlinks to make Ansible easily accessible
    ln -s /opt/ansible_venv/bin/ansible /usr/local/bin/ansible && \
    ln -s /opt/ansible_venv/bin/ansible-playbook /usr/local/bin/ansible-playbook && \

    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER jenkins

{% endhighlight %}

Build and run this universal Jenkins image to mount Jenkins home directory and Docker socket from the host to the container, also add Docker group to the container so Jenkins can run Docker commands inside the container without needing root privileges.

{% highlight shell %}

docker build -t jenkins-all .

docker run -d --name jenkins -p 8080:8080 -p 50000:50000 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /var/jenkins_home:/var/jenkins_home \
--group-add $(getent group docker | cut -d: -f3) \ 
jenkins-all

{% endhighlight %}

- Universal Jenkins CI pipeline design

After installing a list of plugins and configuring all credentials and the GitHub webhook, the CI pipeline is designed bellow and can be triggered by a Git push event and will run automatically:

1. Enable multi-language artifact build support.
2. Integrate testing of Java versions.
3. Enable security checks for static code analysis and Docker image scanning.
4. Implement advanced Jenkins pipeline structuring using <b>try-catch</b>, <b>if-else</b>, <b>timeouts</b>,<b>environment variables</b>,<b>post actions</b> and <b>error handling</b>.

{% highlight shell %}
#  Jenkinsfile

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
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub' // Docker Hub credentials
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
        // for Code Security Analysis and Fixes
        stage('snyk_analysis') {
            steps {
                script {
                    echo 'Running Snyk security analysis...'
                    timeout(time: 5, unit: 'MINUTES') {  // Adjust the timeout value as necessary
                        try {
                            snykSecurity(
                                snykInstallation: SNYK_INSTALLATION,
                                snykTokenId: SNYK_TOKEN,
                                failOnIssues: false,
                                monitorProjectOnBuild: true,
                                additionalArguments: '--severity-threshold=low'
                            )
                       } catch (Exception e) {
                            currentBuild.result = 'FAILURE'
                            error("Error during snyk_analysis: ${e.message}")
                        }
                    }
                }
            }
        }
        
        // Language-specific build and test stages
        stage('Frontend Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('package.json')) {
                            sh 'npm install --force'
                            sh 'npm test'
                        } else {
                            echo 'No package.json found, skipping Frontend build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Frontend build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Java Spring Boot Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('pom.xml')) {
                            sh 'mvn clean package'
                            sh 'mvn test'
                        } else {
                            echo 'No pom.xml found, skipping Java Spring Boot build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Java Spring Boot build and test: ${e.message}")
                    }
                }
            }
        }

        stage('.NET Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('YourSolution.sln')) {
                            sh 'dotnet build'
                            sh 'dotnet test'
                        } else {
                            echo 'No YourSolution.sln found, skipping .NET build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during .NET build and test: ${e.message}")
                    }
                }
            }
        }

        stage('PHP Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('composer.json')) {
                            sh 'composer install'
                            sh 'phpunit'
                        } else {
                            echo 'No composer.json found, skipping PHP build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during PHP build and test: ${e.message}")
                    }
                }
            }
        }

        stage('iOS Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('YourProject.xcodeproj')) {
                            xcodebuild(buildDir: 'build', scheme: 'YourScheme')
                        } else {
                            echo 'No YourProject.xcodeproj found, skipping iOS build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during iOS build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Android Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('build.gradle')) {
                            sh './gradlew build'
                            sh './gradlew test'
                        } else {
                            echo 'No build.gradle found, skipping Android build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Android build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Ruby on Rails Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('Gemfile.lock')) {
                            sh 'bundle install'
                            sh 'bundle exec rake db:migrate'
                            sh 'bundle exec rails test'
                        } else {
                            echo 'No Gemfile.lock found, skipping Ruby on Rails build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Ruby on Rails build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Flask Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('app.py')) {
                            sh 'pip install -r requirements.txt'
                            sh 'python -m unittest discover'
                        } else {
                            echo 'No app.py found, skipping Flask build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Flask build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Django Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('manage.py')) {
                            sh 'pip install -r requirements.txt'
                            sh 'python manage.py migrate'
                            sh 'python manage.py test'
                        } else {
                            echo 'No manage.py found, skipping Django build and test.'
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Django build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Rust Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('Cargo.toml')) {
                            env.RUST_BACKTRACE = 'full'
                            sh 'cargo build'
                            sh 'cargo test'
                        } else {
                            echo "No Cargo.toml file found. Skipping Rust build and test."
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Rust build and test: ${e.message}")
                    }
                }
            }
        }

        stage('Ruby Sinatra Build and Test') {
            steps {
                script {
                    try {
                        if (fileExists('app.rb')) {
                            sh 'gem install bundler'
                            sh 'bundle install'
                            sh 'bundle exec rake test'
                        } else {
                            echo "No app.rb file found. Skipping Ruby Sinatra build and test."
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Error during Ruby Sinatra build and test: ${e.message}")
                    }
                }
            }
        }
        // Build ZackBlog docker image 
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
        // Scan docker image with Trivy
        stage('Docker Image Scan') {
            steps {
                // Use Trivy to scan the built Docker image
                sh "trivy image --severity HIGH,CRITICAL ${IMAGE_NAME}:${IMAGE_TAG} > ${TRIVY_OUTPUT}"
            }
        }
        //Push to Dockerhub
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
        //Output image scan result
        stage('Display Trivy Scan Results') {
            steps {
                script {
                    // Display the contents of the Trivy report
                    def scanReport = readFile("${TRIVY_OUTPUT}")
                    echo "Trivy Scan Report:\n${scanReport}"
                }
            }
        }
        // Additional stages like Docker build, image scan, etc.
    }
    // Post Build Emailing 
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
{% endhighlight %}

- Pipeline test and debug

After thorough testing and validation, the CI pipeline finally works like a charm.

![image tooltip here](/assets/jenkins1.png)

Next, I will create a CD pipeline to integrate with Ansible, AWS, and Terraform to deploy the blog onto AWS EC2, ECS, and EKS.





