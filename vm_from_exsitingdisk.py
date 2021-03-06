"""Create and manage virtual machines.

This script expects that the following environment vars are set:

AZURE_TENANT_ID: your Azure Active Directory tenant id or domain
AZURE_CLIENT_ID: your Azure Active Directory Application Client ID
AZURE_CLIENT_SECRET: your Azure Active Directory Application Secret
AZURE_SUBSCRIPTION_ID: your Azure Subscription Id
"""
import os
import traceback

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import DiskCreateOption

from msrestazure.azure_exceptions import CloudError

from haikunator import Haikunator
haikunator = Haikunator()

# Azure Datacenter
LOCATION = 'westus'

# Resource Group
GROUP_NAME = 'azure-sample-group-virtual-machines'

# Network
VNET_NAME = 'azure-sample-vnet'
SUBNET_NAME = 'azure-sample-subnet'

# VM
IP_CONFIG_NAME = 'azure-sample-ip-config'
NIC_NAME = 'azure-sample-nic'
VM_NAME = 'VmName'

#VM OS Disk
OS_DISK_RESOURCEID = '/subscriptions/a9aaeba6-6cd0-4af5-9bcf-5755eeb28ca2/resourceGroups/exam0508/providers/Microsoft.Compute/disks/VmName_disk1_e4a4a5dbc3ee47618fa799154e9519d4'

def get_credentials():
    subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
    credentials = ServicePrincipalCredentials(
        client_id=os.environ['AZURE_CLIENT_ID'],
        secret=os.environ['AZURE_CLIENT_SECRET'],
        tenant=os.environ['AZURE_TENANT_ID']
    )
    return credentials, subscription_id


def run_example():
    """Virtual Machine management example."""
    #
    # Create all clients with an Application (service principal) token provider
    #
    credentials, subscription_id = get_credentials()
    resource_client = ResourceManagementClient(credentials, subscription_id)
    compute_client = ComputeManagementClient(credentials, subscription_id)
    network_client = NetworkManagementClient(credentials, subscription_id)

    ###########
    # Prepare #
    ###########

    # Create Resource group
    print('\nCreate Resource Group')
    resource_client.resource_groups.create_or_update(GROUP_NAME, {'location': LOCATION})

    try:
        # Create a NIC
        nic = create_nic(network_client)

        #############
        # VM Sample #
        #############

        # Create Linux VM From Custom Image
        print('\nCreating Linux Virtual Machine From Existing Disk')
        vm_parameters = create_vm_customeimage_parameters(nic.id, OS_DISK_RESOURCEID)
        async_vm_creation = compute_client.virtual_machines.create_or_update(
            GROUP_NAME, VM_NAME, vm_parameters)
        async_vm_creation.wait()

        # Tag the VM
        print('\nTag Virtual Machine')
        async_vm_update = compute_client.virtual_machines.create_or_update(
            GROUP_NAME,
            VM_NAME,
            {
                'location': LOCATION,
                'tags': {
                    'who-rocks': 'python',
                    'where': 'on azure'
                }
            }
        )
        async_vm_update.wait()

        # Deallocating the VM
        print('\nDeallocating the VM')
        async_vm_deallocate = compute_client.virtual_machines.deallocate(GROUP_NAME, VM_NAME)
        async_vm_deallocate.wait()

    except CloudError:
        print('A VM operation failed:\n{}'.format(traceback.format_exc()))
    else:
        print('All example operations completed successfully!')
    finally:
        '''
        # Delete Resource group and everything in it
        print('\nDelete Resource Group')
        delete_async_operation = resource_client.resource_groups.delete(GROUP_NAME)
        delete_async_operation.wait()
        print("\nDeleted: {}".format(GROUP_NAME))
        '''

def create_nic(network_client):
    """Create a Network Interface for a VM.
    """
    # Create VNet
    print('\nCreate Vnet')
    async_vnet_creation = network_client.virtual_networks.create_or_update(
        GROUP_NAME,
        VNET_NAME,
        {
            'location': LOCATION,
            'address_space': {
                'address_prefixes': ['10.0.0.0/16']
            }
        }
    )
    async_vnet_creation.wait()

    # Create Subnet
    print('\nCreate Subnet')
    async_subnet_creation = network_client.subnets.create_or_update(
        GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        {'address_prefix': '10.0.0.0/24'}
    )
    subnet_info = async_subnet_creation.result()

    # Create NIC
    print('\nCreate NIC')
    async_nic_creation = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        {
            'location': LOCATION,
            'ip_configurations': [{
                'name': IP_CONFIG_NAME,
                'subnet': {
                    'id': subnet_info.id
                }
            }]
        }
    )
    return async_nic_creation.result()


def create_vm_customeimage_parameters(nic_id, vm_reference):
    """Create the VM parameters structure.
    """
    return {
        'location': LOCATION,
        'hardware_profile': {
            'vm_size': 'Standard_DS1_v2'
        },
        'storage_profile': {
            'osDisk': {
                'osType': 'Linux',
                'createOption': 'Attach',
                'managedDisk': {
                'id': OS_DISK_RESOURCEID
                }
            }
        },
        'network_profile': {
            'network_interfaces': [{
                'id': nic_id,
            }]
        },
    }

if __name__ == "__main__":
    run_example()
