#!/bin/bash

cat >$HOME/.bashrc <<EOF
local=\$HOME/.local
export PATH=\$local/bin:\$PATH
export PATH=\$local/go/bin:\$PATH
export PATH=\$local/maude:\$PATH
EOF

source $HOME/.bashrc
mkdir -p $local $local/bin

go version
if [ $? -ne 0 ]; then
    # install Go
    wget https://go.dev/dl/go1.25.1.linux-amd64.tar.gz
    rm -rf $local/go
    tar -C $local -zxf go1.25.1.linux-amd64.tar.gz
    rm go1.25.1.linux-amd64.tar.gz
    go version
fi

maude --version
if [ $? -ne 0 ]; then
    wget https://github.com/maude-lang/Maude/releases/download/Maude3.5.1/Maude-3.5.1-linux-x86_64.zip
    rm -rf $local/maude
    unzip Maude-3.5.1-linux-x86_64.zip -d $local/maude
    rm Maude-3.5.1-linux-x86_64.zip
    maude --version
fi

python3 --version

terraform version
if [ $? -ne 0 ]; then
    # install terraform
    wget https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_linux_amd64.zip
    rm -f $local/bin/terraform
    unzip terraform_1.13.5_linux_amd64.zip -d $local/bin
    rm terraform_1.13.5_linux_amd64.zip
    terraform version
fi

# install the provider
exp_repo="$(realpath $(dirname $0))/../synthetic-cases/"
cd "$exp_repo/provider-simple/"
go mod tidy
go build .
mv terraform-provider-myprovider "$local/go/bin"
cat > $HOME/.terraformrc <<EOF
provider_installation {
dev_overrides {
    "example/myprovider" = "$local/go/bin"
}
direct {}
}
EOF

