# odin-infrastructure
Network and services for basic functionality

Note that many other stacks use the VPC, which may lead to many invisible dependencies.

QSMR-services in odin-l2-lambda (despite the name) runs in the Odin-API cluster, which also is a hidden dependency.

Network interfaces might be laying around in the VPC.

## accessing odin.mongo

```bash
eval "$(ssh-agent -s)"
ssh-add key.pem
ssh -A -J ec2-user@admin.odin-smr.org ec2-user@mongo.odin
```
