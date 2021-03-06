node {
	def vm
	def ipaddr
	def instanceid
	def timestamp

	stage('Build') {
		checkout scm
		sh "./create_archive.sh --source-dir \$(pwd) --destination-dir /tmp/vnflcv --twister-dir /tmp/twister"
		sh "ls -l /tmp/vnflcv"
		timestamp = sh(script: "date '+%Y%m%d-%H%M%S' | tr -d '\n'", returnStdout: true)
	}

	stage('Provision') {
		vm = openstackMachine cloud: 'mirantis', template: 'vnflcv'
		ipaddr = vm.getAddress()
		instanceid = vm.getId()
	}

	stage('Connect') {
		sh "ssh-keygen -f ~/.ssh/known_hosts -R $ipaddr"
		sh "ssh -o StrictHostKeyChecking=no -o ConnectionAttempts=600 ubuntu@$ipaddr true"
	}

	stage('Upload') {
		sh "scp /tmp/vnflcv/vnflcv.tar.gz ubuntu@$ipaddr:~"
		sh "ssh ubuntu@$ipaddr tar -xvf vnflcv.tar.gz"
	}

	stage('Deploy') {
		try {
			timeout(time: 60, unit: 'MINUTES') {
				sh "ssh ubuntu@$ipaddr vnflcv/deploy.sh --headless"
			}
		} finally {
			sh "ssh ubuntu@$ipaddr cat .cache/conjure-up/conjure-up.log"
			sh "ssh ubuntu@$ipaddr /snap/bin/juju status"
		}
	}

	stage('Configure') {
		sh "curl -f -XPUT http://$ipaddr:8080/v1.0/mano/tacker1 -H 'Content-Type: Application/json' -d @/tmp/vnflcv/mano.json"
		sh "curl -f -XPUT http://$ipaddr:8080/v1.0/traffic/stc1 -H 'Content-Type: Application/json' -d @/tmp/vnflcv/traffic.json"
		sh "curl -f -XPUT http://$ipaddr:8080/v1.0/env/lab1 -H 'Content-Type: Application/json' -d @/tmp/vnflcv/env.json"
		sh "echo '\"lab1\"' | curl -f -XPUT http://$ipaddr:8080/v1.0/config/active-env -H 'Content-Type: Application/json' -d @-"
		sh "echo '\"SP1\"' | curl -f -XPUT http://$ipaddr:8080/v1.0/config/scaling_policy_name -H 'Content-Type: Application/json' -d @-"
	}

	stage('Run') {
		executionid = sh(script: "curl -XPOST http://$ipaddr:8080/v1.0/exec -H 'Content-Type: Application/json' -d @/tmp/vnflcv/tc_exec.json | jq -r '.execution_id' | tr -d '\n'", returnStdout: true)
		sh "curl http://$ipaddr:8080/v1.0/wait/$executionid"
		sh "curl http://$ipaddr:8080/v1.0/exec/$executionid -H 'Content-Type: Application/json' | python -mjson.tool"
		sh "ssh ubuntu@$ipaddr /snap/bin/juju ssh vnflcv/0 cat /var/log/vnflcv/\\\'*.log\\\'"
		sh "ssh ubuntu@$ipaddr /snap/bin/juju ssh vnflcv/0 cat /var/log/vnflcv/\\\'*.txt\\\'"
		sh "ssh ubuntu@$ipaddr /snap/bin/juju ssh vnflcv/0 journalctl -u vnflcv-rest"
		sh "test \$(curl http://$ipaddr:8080/v1.0/exec/$executionid -H 'Content-Type: Application/json' | jq -r '.tc_result|.overall_status') = PASSED"
		sh "curl -f -XDELETE http://$ipaddr:8080/v1.0/mano/tacker1"
		sh "curl -f -XDELETE http://$ipaddr:8080/v1.0/traffic/stc1"
		sh "curl -f -XDELETE http://$ipaddr:8080/v1.0/env/lab1"
		sh "curl -f -XDELETE http://$ipaddr:8080/v1.0/config/active-env"
		sh "curl -f -XDELETE http://$ipaddr:8080/v1.0/config/scaling_policy_name"
	}

	stage('Publish') {
		sh "cp /tmp/vnflcv/vnflcv.tar.gz /var/www/html/vnflcv/vnflcv-${timestamp}.tar.gz"
	}

	stage('Snapshot') {
                sh """
			. /tmp/vnflcv/openrc
			imageid=\$(nova image-create --show --poll $instanceid vnflcv-$timestamp | grep -w id | tr -s ' ' | cut -f 4 -d ' ')
			glance image-download \$imageid --file /tmp/vnflcv/vnflcv-${timestamp}.qcow2
			glance image-delete \$imageid
			rm -v /var/www/html/vnflcv/*.qcow2 || true
			qemu-img convert -c /tmp/vnflcv/vnflcv-${timestamp}.qcow2 -O qcow2 /var/www/html/vnflcv/vnflcv-${timestamp}.qcow2
			rm -v /tmp/vnflcv/vnflcv-${timestamp}.qcow2
                """
        }
}
