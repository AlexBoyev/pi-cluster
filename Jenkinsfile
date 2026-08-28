pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    environment {
        PROJECT_DIR = '/home/admin/pi-cluster'
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/AlexBoyev/pi-cluster',
                    branch: 'master'
            }
        }

        stage('Sync') {
            steps {
                sh '''
                    rsync -a --delete \
                        --exclude='.git' \
                        --exclude='.env' \
                        --exclude='__pycache__' \
                        --exclude='*.pyc' \
                        --exclude='node_modules' \
                        $WORKSPACE/ $PROJECT_DIR/
                '''
            }
        }

        stage('Migrate') {
            steps {
                sh 'cd $PROJECT_DIR && docker compose run --rm backend alembic upgrade head'
            }
        }

        stage('Deploy') {
            steps {
                sh 'cd $PROJECT_DIR && docker compose up -d --build backend frontend'
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    sleep 10
                    curl -sf http://10.100.102.10:8000/health \
                        && echo "Backend healthy" \
                        || (echo "Backend health check FAILED" && exit 1)
                '''
            }
        }
    }

    post {
        success { echo "Build #${BUILD_NUMBER} deployed successfully." }
        failure { echo "Build #${BUILD_NUMBER} FAILED." }
    }
}
