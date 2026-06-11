pipeline {

    agent any

    environment {
        DEPLOY_HOST = credentials('deploy-ssh-host')
        DEPLOY_PATH = '/opt/data-processor'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {

        stage('Setup') {
            steps {
                sh """
                    rm -rf .venv
                    python3.11 -m venv .venv
                    .venv/bin/pip install --upgrade pip
                    .venv/bin/pip install -r requirements.txt
                    mkdir -p reports
                """
            }
        }

        stage('Lint') {
            steps {
                sh ".venv/bin/flake8 src/ tests/ --max-line-length=100 --statistics"
            }
        }

        stage('Unit Tests') {
            steps {
                sh """
                    .venv/bin/pytest tests/unit/ \
                        --junitxml=reports/unit_results.xml \
                        --cov=src \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-report=html:reports/coverage_html \
                        --cov-fail-under=80 \
                        -v
                """
            }
            post {
                always {
                    junit 'reports/unit_results.xml'
                }
            }
        }

        stage('Integration Tests') {
            steps {
                sh """
                    .venv/bin/pytest tests/integration/ \
                        --junitxml=reports/integration_results.xml \
                        -v
                """
            }
            post {
                always {
                    junit 'reports/integration_results.xml'
                }
            }
        }

        stage('Publish Reports') {
            steps {
                archiveArtifacts artifacts: 'reports/**', fingerprint: true
                publishHTML(target: [
                    allowMissing         : false,
                    alwaysLinkToLastBuild: true,
                    keepAll              : true,
                    reportDir            : 'reports/coverage_html',
                    reportFiles          : 'index.html',
                    reportName           : 'Coverage Report'
                ])
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sshagent(credentials: ['deploy-ssh-key']) {
                    sh """
                        rsync -avz --delete \
                            --exclude='__pycache__' \
                            --exclude='*.pyc' \
                            src/ ${DEPLOY_HOST}:${DEPLOY_PATH}/src/
                        ssh ${DEPLOY_HOST} "cd ${DEPLOY_PATH} && pip install -r requirements.txt"
                    """
                }
            }
        }
    }

    post {
        success {
            echo "all good"
        }
        failure {
            echo "something broke, check the logs"
        }
        always {
            cleanWs(patterns: [[pattern: '.venv/**', type: 'INCLUDE']])
        }
    }
}
