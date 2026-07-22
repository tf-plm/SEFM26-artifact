package resource_simple

import (
	"context"
	"fmt"
    "time"
    "strings"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-log/tflog"
)

var (
	_ resource.Resource = &SimpleResource{}
)

func NewSimpleResource() resource.Resource {
	return &SimpleResource{}
}

type SimpleResource struct{}

type SimpleResourceModel struct {
	Name types.String `tfsdk:"name"`
}

func sleep(r SimpleResourceModel) {
    if strings.Contains(r.Name.String(), "A") {
        time.Sleep(500*time.Millisecond)
    } else {
        time.Sleep(1000*time.Millisecond)
    }
}

func (r *SimpleResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_simple"
}

func (r *SimpleResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"name": schema.StringAttribute{
				Required:    true,
				Description: "The name of the resource",
			},
		},
	}
}

func (r *SimpleResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan SimpleResourceModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
    // sleep(plan)
	tflog.Info(ctx, fmt.Sprintf("[CREATE] name=%s", plan.Name.ValueString()))
	resp.State.Set(ctx, plan)
}

func (r *SimpleResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state SimpleResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	tflog.Info(ctx, fmt.Sprintf("[READ] name=%s", state.Name.ValueString()))
	resp.State.Set(ctx, state)
}

func (r *SimpleResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan SimpleResourceModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
    // sleep(plan)
	tflog.Info(ctx, fmt.Sprintf("[UPDATE] name=%s", plan.Name.ValueString()))
	resp.State.Set(ctx, plan)
}

func (r *SimpleResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state SimpleResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
    // sleep(state)
	tflog.Info(ctx, fmt.Sprintf("[DELETE] name=%s", state.Name.ValueString()))
}
