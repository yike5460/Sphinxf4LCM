# VNFLifeCycleValidation
*VNF Lifecycle Validation*
This directory includes the work resulted from VNF Lifecycle test automation project by Luxoft
___

# Prerequisites
1. Make sure you have a clean Ubuntu 16.04.2 virtual machine.
- Suggested virtual resources: 2 CPUs, 8 GB RAM, 32 GB Disk
- The VM must have Internet access (for getting the required Ubuntu packages).

2. Login with non-root user with sudo capabilities.
___

# Installation
1. Unpack the *VNF LifeCycle Validation* archive:

   ```# tar zxvf vnflcv.tar.gz```
2. Go to the VNF LifeCycle Validation folder:

   ```# cd ./vnflcv```

3. Run the deployment script:

   ```# ./deploy.sh```

4. After all the system upgrades and software installations are performed, conjure-up will be launched. You will be asked for the following inputs:
   - "Where would you like to deploy?"
      You can use the default value of "localhost". "localhost" means LXC containers hosted on the VM itself.
   - "Select a network bridge and storage pool for this deployment:"
      You can use the default falues of "lxdbr0" for network bridge and "default" for storage pool.
   -  "Configure the public IP used to reach this VM. It could be an IP address configured on the VM itself, a floating IP from Openstack, a public IP used for NAT etc."
      Here you have to enter the IP address at which this machine is reachable from outside.
   -  "5 Applications in vnflcv:"
      You can use the button "Deploy all 5 Remaining Applications" to begin deployment. The deployment will take 20-30 minutes.
5. When conjure-up finishes deployment it will display the details to reach the applications. Use a browser to access the specified web resources.
 
