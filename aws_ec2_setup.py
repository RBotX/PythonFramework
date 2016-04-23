
#SETTING UP SINGLE EC2 COMPUTER

#Note: This assumes the ec2 instance is running ubuntu

wget https://3230d63b5fc54e62148e-c95ac804525aac4b6dba79b00b39d1d3.ssl.cf1.rackcdn.com/Anaconda2-2.4.1-Linux-x86_64.sh
bash Anaconda2-2.4.1-Linux-x86_64.sh -b
source .bashrc

sudo apt-get update
sudo apt-get -y install git libatlas-base-dev gfortran python-dev python-pip python-numpy python-scipy python-nose

#Note the following may be necessary: https://github.com/ContinuumIO/anaconda-issues/issues/244
sudo apt-get -y install python-qt4

#Note that this DOES NOT use sudo
pip install cvxpy
nosetests cvxpy
pip install sklearn

git clone https://github.com/adgress/PythonFramework.git


#Install MPI: http://glennklockwood.blogspot.com/2013/04/quick-mpi-cluster-setup-on-amazon-ec2.html
sudo apt-get -y install mpich-devel

"Move private key to 'ubuntu/.ssh/', rename to 'id_rsa'"

'Add the following lines to .bashrc:'
'''
export PATH=/usr/lib64/openmpi/bin:$PATH'
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib
'''
source .bashrc


#SETTING UP STARCLUSTER

#Set up MPI cluster: http://mpitutorial.com/tutorials/launching-an-amazon-ec2-mpi-cluster/
sudo easy_install StarCluster
starcluster help
'Select '2' to create StarCluster config file'
'Enter access key info into config file'
starcluster createkey mykey -o ~/.ssh/mykey.rsa
'Add following to config file:'
'''
[key mykey]
KEY_LOCATION = ~/.ssh/mykey.rsa
'''

'Update the following as necessary:'
'''
[cluster smallcluster]
KEYNAME = mykey
CLUSTER_SIZE = 2
CLUSTER_USER = sgeadmin
CLUSTER_SHELL = bash
NODE_IMAGE_ID = ami-899d49e0
NODE_INSTANCE_TYPE = m1.small
'''

'Set starcluster to use MPICH2 - http://star.mit.edu/cluster/docs/0.93.3/plugins/mpich2.html

#
starcluster start mpicluster
starcluster sshmaster mpicluster
pip install cvxpy sklearn
nosetests cvxpy

