import * as cdk from 'aws-cdk-lib';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import { Construct } from 'constructs';

export interface DomainStackProps extends cdk.StackProps {
  domainName: string;
}

export class DomainStack extends cdk.Stack {
  public readonly hostedZone: route53.IHostedZone;
  public readonly certificate: acm.Certificate;
  public readonly cloudfrontCertificate: acm.ICertificate;

  constructor(scope: Construct, id: string, props: DomainStackProps) {
    super(scope, id, props);

    const { domainName } = props;

    // Create or import hosted zone
    this.hostedZone = new route53.HostedZone(this, 'HostedZone', {
      zoneName: domainName,
    });

    // Certificate for API Gateway (regional, in us-west-2)
    this.certificate = new acm.Certificate(this, 'Certificate', {
      domainName,
      subjectAlternativeNames: [`*.${domainName}`],
      validation: acm.CertificateValidation.fromDns(this.hostedZone),
    });

    // Certificate for CloudFront (MUST be in us-east-1)
    this.cloudfrontCertificate = new acm.DnsValidatedCertificate(this, 'CloudFrontCertificate', {
      domainName,
      subjectAlternativeNames: [`*.${domainName}`],
      hostedZone: this.hostedZone,
      region: 'us-east-1', // CloudFront requires certs in us-east-1
    });

    // Output nameservers for GoDaddy configuration
    new cdk.CfnOutput(this, 'NameServers', {
      value: cdk.Fn.join(', ', this.hostedZone.hostedZoneNameServers || []),
      description: 'Update these nameservers in GoDaddy DNS settings',
    });

    // Output certificate ARN
    new cdk.CfnOutput(this, 'CertificateArn', {
      value: this.certificate.certificateArn,
      description: 'ACM Certificate ARN (regional)',
    });

    new cdk.CfnOutput(this, 'CloudFrontCertificateArn', {
      value: this.cloudfrontCertificate.certificateArn,
      description: 'ACM Certificate ARN (us-east-1 for CloudFront)',
    });
  }
}

