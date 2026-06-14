pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'bash jenkins/run-tests.sh'
            }
        }
        stage('Deploy') {
            when {
                expression {
                    def b = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
                    return b.contains('master')
                }
            }
            steps {
                sh 'bash deploy.sh'
            }
        }
        stage('Health') {
            when {
                expression {
                    def b = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
                    return b.contains('master')
                }
            }
            steps {
                sh 'curl -sf http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health'
            }
        }
    }
}
