pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'pip install -r infra-service/requirements.txt pytest httpx'
                sh 'cd infra-service && PYTHONPATH=src pytest tests -q'
            }
        }
        stage('Deploy') {
            when { branch 'master' }
            steps {
                sh 'bash deploy.sh'
            }
        }
        stage('Health') {
            when { branch 'master' }
            steps {
                sh 'curl -sf http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health'
            }
        }
    }
}
