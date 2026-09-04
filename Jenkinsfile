pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 25, unit: 'MINUTES')
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
                        --exclude='backend/kubeconfig' \
                        $WORKSPACE/ $PROJECT_DIR/
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    cd $PROJECT_DIR
                    docker compose build backend frontend dnsmasq
                    docker compose pull nginx
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    cd $PROJECT_DIR
                    docker compose run --rm --no-deps \
                        -e DATABASE_URL=sqlite+aiosqlite:///./test_ci.db \
                        -e SECRET_KEY=ci-test-secret \
                        -e ADMIN_DEFAULT_PASSWORD=adminpass123 \
                        -e SSH_USERNAME=pi \
                        -e SSH_PASSWORD=test \
                        -e K8S_KUBECONFIG_PATH=/tmp/kubeconfig \
                        -e PROMETHEUS_URL=http://localhost:9090 \
                        backend \
                        sh -c "rm -f ./test_ci.db && pip install pytest pytest-asyncio httpx aiosqlite --quiet && pytest tests/ -v --tb=short"
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    cd $PROJECT_DIR
                    SERVICES=$(docker compose config --services | grep -v "^jenkins$" | tr "\n" " ")
                    docker compose up -d $SERVICES
                    docker restart pi-cluster-nginx-1
                '''
            }
        }

        stage('Migrate') {
            steps {
                sh '''
                    sleep 5
                    cd $PROJECT_DIR && docker compose exec -T backend alembic upgrade head
                '''
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

        stage('Push to Registry') {
            steps {
                sh '''
                    cd $PROJECT_DIR
                    TAG=$(echo "$GIT_COMMIT" | cut -c1-7)
                    for svc in backend frontend; do
                        docker tag pi-cluster-$svc:latest localhost:5000/pi-cluster-$svc:$TAG
                        docker tag pi-cluster-$svc:latest localhost:5000/pi-cluster-$svc:latest
                        docker push localhost:5000/pi-cluster-$svc:$TAG
                        docker push localhost:5000/pi-cluster-$svc:latest
                    done
                '''
            }
        }
    }

    post {
        success { echo "Build #${BUILD_NUMBER} deployed successfully." }
        failure { echo "Build #${BUILD_NUMBER} FAILED." }
    }
}
