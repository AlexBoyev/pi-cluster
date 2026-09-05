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
                    # prometheus.yml/alerts.yml are bind-mounted as individual
                    # FILES, not a directory - `up -d` alone won't recreate
                    # prometheus for a content-only change (compose only
                    # tracks its own declared config, not a mounted file's
                    # content), and a plain `-/reload` doesn't help either:
                    # rsync (this stage's own sync step, without --inplace)
                    # replaces the file via a new inode on every deploy, and
                    # a single-file Docker bind mount stays pinned to the
                    # inode it resolved at container-start - a long-running
                    # container keeps serving that orphaned old inode
                    # forever, reload or not. Confirmed live: `docker exec
                    # prometheus cat alerts.yml` showed 21-hour-stale content
                    # despite a fresh host-side write and a successful
                    # `-/reload` call. Only recreating the container
                    # re-resolves the mount.
                    docker compose up -d --force-recreate prometheus
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
                    for i in $(seq 1 12); do
                        if curl -sf http://10.100.102.10:8000/health; then
                            echo "Backend healthy (attempt $i)"
                            exit 0
                        fi
                        echo "Backend not ready yet, retrying in 5s ($i/12)..."
                        sleep 5
                    done
                    echo "Backend health check FAILED after 60s"
                    exit 1
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
