package main

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"
)

func main() {
	providerserver.Serve(context.Background(), New, providerserver.ServeOpts{
		Address: "registry.terraform.io/example/myprovider",
	})
}
