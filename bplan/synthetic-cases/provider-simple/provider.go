package main

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/resource"

	"mutable-tf-plm/synthetic-cases/terraform-provider-myprovider/resource_simple"
)

var _ provider.Provider = &MyProvider{}

type MyProvider struct{}

// Metadata defines the provider name (prefix).
func (p *MyProvider) Metadata(_ context.Context, req provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "myprovider"
}

// Schema defines provider-level configuration (none here).
func (p *MyProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
}

// Configure configures the provider (no-op for now).
func (p *MyProvider) Configure(_ context.Context, _ provider.ConfigureRequest, _ *provider.ConfigureResponse) {
}

// Resources defines which resources this provider supports.
func (p *MyProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		resource_simple.NewSimpleResource,
	}
}

// DataSources defines which data sources this provider supports (none here).
func (p *MyProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return nil
}

// New returns a new instance of the provider.
func New() provider.Provider {
	return &MyProvider{}
}
