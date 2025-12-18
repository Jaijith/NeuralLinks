import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as events from 'aws-cdk-lib/aws-events';
import * as eventsTargets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';
import * as path from 'path';

export interface BackendStackProps extends cdk.StackProps {
  domainName: string;
  certificate: acm.ICertificate;
  hostedZone: route53.IHostedZone;
}

export class BackendStack extends cdk.Stack {
  public readonly apiGatewayUrl: string;
  public readonly uploadsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: BackendStackProps) {
    super(scope, id, props);

    const { domainName, certificate, hostedZone } = props;

    // S3 bucket for file uploads (public read for images)
    this.uploadsBucket = new s3.Bucket(this, 'UploadsBucket', {
      bucketName: `2n1-uploads-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      // Allow public read access for uploaded images
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: false,
        ignorePublicAcls: false,
        blockPublicPolicy: false,
        restrictPublicBuckets: false,
      }),
      publicReadAccess: true, // Allow public read
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
      lifecycleRules: [
        {
          id: 'DeleteIncompleteUploads',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
        {
          id: 'ArchiveOldFiles',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
    });

    // Lambda function for FastAPI backend (using container image for large dependencies)
    const backendFunction = new lambda.DockerImageFunction(this, 'BackendFunction', {
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../backend'), {
        file: 'Dockerfile',
        // Force rebuild by adding a build arg that changes
        buildArgs: {
          BUILD_DATE: new Date().toISOString(),
        },
        // CRITICAL: Build for x86_64 architecture (Lambda default)
        // This is required when building on ARM Macs (M1/M2)
        platform: ecr_assets.Platform.LINUX_AMD64,
      }),
      // Set Lambda architecture to x86_64
      architecture: lambda.Architecture.X86_64,
      memorySize: 2048, // Increased for container image
      timeout: cdk.Duration.seconds(120), // Increased for autonomous avatar cycles
      environment: {
        AWS_S3_BUCKET: this.uploadsBucket.bucketName,
        AWS_S3_REGION: this.region, // Set S3 region to match bucket region
        STORAGE_TYPE: 's3',
        CORS_ORIGINS: `https://${domainName},https://www.${domainName}`,
        GOOGLE_REDIRECT_URI: `https://api.${domainName}/api/auth/google/callback`,
        YOUTUBE_REDIRECT_URI: `https://api.${domainName}/api/integrations/oauth/callback/youtube`,
        BACKEND_URL: `https://api.${domainName}`,
        FRONTEND_URL: `https://${domainName}`,
      },
    });

    // Grant Lambda permissions to access S3
    this.uploadsBucket.grantReadWrite(backendFunction);

    // Grant Lambda permissions to read secrets
    const mongodbSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'MongoDBSecret',
      '2n1/mongodb/uri'
    );
    mongodbSecret.grantRead(backendFunction);

    const googleClientIdSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'GoogleClientIdSecret',
      '2n1/google/client-id'
    );
    googleClientIdSecret.grantRead(backendFunction);

    const googleClientSecretSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'GoogleClientSecretSecret',
      '2n1/google/client-secret'
    );
    googleClientSecretSecret.grantRead(backendFunction);

    // OpenAI API Key secret
    const openaiApiKeySecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'OpenAIApiKeySecret',
      '2n1/openai/api-key'
    );
    openaiApiKeySecret.grantRead(backendFunction);

    // Add secrets to Lambda environment (will be fetched at runtime)
    // Note: AWS_REGION is automatically set by Lambda runtime, don't set it manually
    backendFunction.addEnvironment('MONGODB_SECRET_NAME', mongodbSecret.secretName);
    backendFunction.addEnvironment('GOOGLE_CLIENT_ID_SECRET_NAME', googleClientIdSecret.secretName);
    backendFunction.addEnvironment('GOOGLE_CLIENT_SECRET_SECRET_NAME', googleClientSecretSecret.secretName);
    backendFunction.addEnvironment('OPENAI_SECRET_NAME', openaiApiKeySecret.secretName);
    backendFunction.addEnvironment('OPENAI_MODEL', 'gpt-4o-mini');

    // API Gateway
    const api = new apigateway.RestApi(this, 'Api', {
      restApiName: '2N1 API',
      description: 'API Gateway for 2N1 backend',
      defaultCorsPreflightOptions: {
        allowOrigins: [`https://${domainName}`, `https://www.${domainName}`],
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'Authorization', 
          'X-Amz-Date',
          'X-Api-Key',
          'X-Requested-With',
          'Accept',
          'Origin',
          'Access-Control-Request-Method',
          'Access-Control-Request-Headers',
        ],
        allowCredentials: true,
        maxAge: cdk.Duration.hours(1),
      },
      domainName: {
        domainName: `api.${domainName}`,
        certificate,
      },
      // Support binary media types for file uploads
      binaryMediaTypes: ['multipart/form-data', 'image/*', 'application/octet-stream'],
      // Increase payload size limit (max 10MB for REST API)
      minCompressionSize: cdk.Size.bytes(0),
    });

    // Lambda integration - proxy mode for FastAPI
    const lambdaIntegration = new apigateway.LambdaIntegration(backendFunction, {
      proxy: true,
    });

    // Proxy all requests to Lambda
    api.root.addProxy({
      defaultIntegration: lambdaIntegration,
      anyMethod: true,
    });

    // Route 53 record for API subdomain
    new route53.ARecord(this, 'ApiARecord', {
      zone: hostedZone,
      recordName: 'api',
      target: route53.RecordTarget.fromAlias(
        new route53Targets.ApiGatewayDomain(api.domainName!)
      ),
    });

    this.apiGatewayUrl = `https://api.${domainName}`;

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.apiGatewayUrl,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'UploadsBucketName', {
      value: this.uploadsBucket.bucketName,
      description: 'S3 bucket for file uploads',
    });

    // EventBridge rule to trigger autonomous avatar cycles every 2 minutes
    const autonomousCycleRule = new events.Rule(this, 'AutonomousCycleRule', {
      ruleName: '2n1-autonomous-avatar-cycle',
      description: 'Triggers autonomous avatar actions every 2 minutes',
      schedule: events.Schedule.rate(cdk.Duration.minutes(2)),
      enabled: true,
    });

    // Add Lambda as target with specific event payload
    autonomousCycleRule.addTarget(new eventsTargets.LambdaFunction(backendFunction, {
      event: events.RuleTargetInput.fromObject({
        source: 'aws.events',
        'detail-type': 'Autonomous Avatar Cycle',
        detail: {
          action: 'run_autonomous_cycle',
          trigger: 'eventbridge_schedule'
        }
      }),
      retryAttempts: 0, // Don't retry - next scheduled run will handle it
    }));

    // Add environment variable for EventBridge API key
    backendFunction.addEnvironment('EVENTBRIDGE_API_KEY', 'neurallinks-autonomous-trigger-2024');

    new cdk.CfnOutput(this, 'AutonomousCycleRuleArn', {
      value: autonomousCycleRule.ruleArn,
      description: 'EventBridge rule for autonomous avatar cycles',
    });
  }
}

