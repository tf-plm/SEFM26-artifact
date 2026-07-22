terraform {
  required_version = ">= 0.14.0"
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.53.0"
    }
  }
}

provider "openstack" {
  user_name = "${var.openstack_access_key}"
  tenant_name = "${var.openstack_tenant_name}"
  cloud = "openstack"
  # auth_url = "${var.openstack_keystone_uri}"
  # password = "${var.openstack_secret_key}"
}
