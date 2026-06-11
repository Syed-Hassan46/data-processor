// =============================================================================
//  Jenkinsfile  –  JSON Data Processor  |  CI/CD Pipeline
//  Stages: Install → Lint → Unit Tests → Integration Tests → Report → Deploy
// =============================================================================

pipeline {

    agent any

    // -------------------------------------------------------------------------
    // Environment & global config
    // -------------------------------------------------------------------------
    environment {
        PYTHON_VERSION  = '3.11'
        VENV_DIR        = '.venv'
        REPORTS_DIR     = 'reports'

        // Change target to your actual deploy host / path
        DEPLOY_HOST     = credentials('deploy-ssh-host')   // Jenkins credential
        DEPLOY_PATH     = '/opt/data-processor'
    }

    options {
        // Keep last 10 builds so report history is accessible
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Abort if the whole pipeline takes longer than 20 minutes
        timeout(time: 20, unit: 'MINUTES')
        // Do not run parallel builds on the same branch
        disableConcurrentBuilds()
        // Timestamps in console log
        timestamps()
    }

    // -------------------------------------------------------------------------
    // Trigger: poll SCM every 5 minutes OR build on push (if webhook configured)
    // -------------------------------------------------------------------------
    triggers {
        pollSCM('H/5 * * * *')
    }

    // =========================================================================
    // STAGES
    // =========================================================================
    stages {

        // ---------------------------------------------------------------------
        // 1. SETUP – create virtual environment & install dependencies
        // ---------------------------------------------------------------------
        stage('Setup') {
            steps {
                echo "==> Setting up Python virtual environment"
                sh """
                    python${PYTHON_VERSION} -m venv ${VENV_DIR}
                    ${VENV_DIR}/bin/pip install --upgrade pip
                    ${VENV_DIR}/bin/pip install -r requirements.txt
                    mkdir -p ${REPORTS_DIR}
                """
            }
        }

        // ---------------------------------------------------------------------
        // 2. LINT – static analysis with flake8
        // ---------------------------------------------------------------------
        stage('Lint') {
            steps {
                echo "==> Running flake8 linter"
                sh "${VENV_DIR}/bin/flake8 src/ tests/ --max-line-length=100 --statistics"
            }
        }

        // ---------------------------------------------------------------------
        // 3. UNIT TESTS
        //    - Runs tests in tests/unit/
        //    - Generates JUnit XML + HTML coverage report
        //    - Uses --lf (last-failed) on re-runs to optimise the test suite
        // ---------------------------------------------------------------------
        stage('Unit Tests') {
            steps {
                echo "==> Running unit tests"
                sh """
                    ${VENV_DIR}/bin/pytest tests/unit/ \
                        --junitxml=${REPORTS_DIR}/unit_results.xml \
                        --cov=src \
                        --cov-report=xml:${REPORTS_DIR}/coverage.xml \
                        --cov-report=html:${REPORTS_DIR}/coverage_html \
                        --cov-fail-under=80 \
                        -v
                """
            }
            post {
                always {
                    // Publish JUnit results so Jenkins shows per-test history
                    junit "${REPORTS_DIR}/unit_results.xml"
                }
            }
        }

        // ---------------------------------------------------------------------
        // 4. INTEGRATION TESTS
        //    - Runs tests in tests/integration/
        //    - Generates separate JUnit XML
        // ---------------------------------------------------------------------
        stage('Integration Tests') {
            steps {
                echo "==> Running integration tests"
                sh """
                    ${VENV_DIR}/bin/pytest tests/integration/ \
                        --junitxml=${REPORTS_DIR}/integration_results.xml \
                        -v
                """
            }
            post {
                always {
                    junit "${REPORTS_DIR}/integration_results.xml"
                }
            }
        }

        // ---------------------------------------------------------------------
        // 5. PUBLISH REPORTS – archive artefacts & publish HTML coverage
        // ---------------------------------------------------------------------
        stage('Publish Reports') {
            steps {
                echo "==> Archiving test reports"
                archiveArtifacts artifacts: "${REPORTS_DIR}/**", fingerprint: true

                publishHTML(target: [
                    allowMissing         : false,
                    alwaysLinkToLastBuild: true,
                    keepAll              : true,
                    reportDir            : "${REPORTS_DIR}/coverage_html",
                    reportFiles          : 'index.html',
                    reportName           : 'Coverage Report'
                ])
            }
        }

        // ---------------------------------------------------------------------
        // 6. DEPLOY – only on main/master branch after all tests pass
        //    Copies the src/ package to the remote server via rsync over SSH.
        // ---------------------------------------------------------------------
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo "==> Deploying to ${DEPLOY_HOST}:${DEPLOY_PATH}"
                sshagent(credentials: ['deploy-ssh-key']) {
                    sh """
                        rsync -avz --delete \
                            --exclude='__pycache__' \
                            --exclude='*.pyc' \
                            src/ \
                            ${DEPLOY_HOST}:${DEPLOY_PATH}/src/
                        ssh ${DEPLOY_HOST} "cd ${DEPLOY_PATH} && pip install -r requirements.txt"
                    """
                }
            }
        }
    }

    // =========================================================================
    // POST-PIPELINE ACTIONS
    // =========================================================================
    post {

        success {
            echo "Pipeline completed successfully."
            // Uncomment to send email on success:
            // mail to: 'team@example.com', subject: "✅ Build #${BUILD_NUMBER} passed", body: "See ${BUILD_URL}"
        }

        failure {
            echo "Pipeline FAILED – check the console output."
            // mail to: 'team@example.com', subject: "❌ Build #${BUILD_NUMBER} failed", body: "See ${BUILD_URL}"
        }

        always {
            echo "Cleaning up workspace..."
            cleanWs(patterns: [[pattern: "${VENV_DIR}/**", type: 'INCLUDE']])
        }
    }
}
