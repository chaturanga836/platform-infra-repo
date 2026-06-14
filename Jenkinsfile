pipeline {
    agent any

    environment {
        DEPLOY_HOST = '13.200.160.10'
        INFRA_SERVICE_PORT = '9000'
    }

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
                sh '''
                    set -e
                    echo "=== Infra service health ==="
                    for i in $(seq 1 24); do
                      if curl -sf "http://${DEPLOY_HOST}:${INFRA_SERVICE_PORT}/health"; then
                        echo "Infra service OK"
                        exit 0
                      fi
                      if [ "$i" -eq 24 ]; then exit 1; fi
                      sleep 5
                    done
                '''
            }
        }
    }
}
