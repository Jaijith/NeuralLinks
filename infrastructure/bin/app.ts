#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FrontendStack } from '../lib/frontend-stack';
import { BackendStack } from '../lib/backend-stack';
import { DomainStack } from '../lib/domain-stack';

const app = new cdk.App();

// Configuration
const config = {
  domainName: '2ness.com',
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  },
};

// Domain Stack (Route 53, ACM certificates)
const domainStack = new DomainStack(app, 'DomainStack', {
  domainName: config.domainName,
  env: config.env,
});

// Backend Stack (Lambda, API Gateway, S3 for uploads)
const backendStack = new BackendStack(app, 'BackendStack', {
  domainName: config.domainName,
  certificate: domainStack.certificate,
  hostedZone: domainStack.hostedZone,
  env: config.env,
});

// Frontend Stack (S3, CloudFront)
// Uses cloudfrontCertificate which is in us-east-1 (required by CloudFront)
const frontendStack = new FrontendStack(app, 'FrontendStack', {
  domainName: config.domainName,
  certificate: domainStack.cloudfrontCertificate,
  hostedZone: domainStack.hostedZone,
  apiGatewayUrl: backendStack.apiGatewayUrl,
  env: config.env,
});

// Add dependencies
frontendStack.addDependency(backendStack);
frontendStack.addDependency(domainStack);
backendStack.addDependency(domainStack);

// Add tags
cdk.Tags.of(app).add('Project', '2N1');
cdk.Tags.of(app).add('Environment', 'production');

