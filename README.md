# Krakow Python: Elastic Beanstalk learning project

## Included
- v1: teal background. v2: orange background. Both show the same cartoon panorama and three cropped detail views, with NO visible homepage text.
- No database, external APIs, JavaScript, fonts or image generation at runtime.
- Python standard-library WSGI app; Gunicorn is the only runtime dependency. One worker, two threads.
- /health returns HTTP 200 with JSON. /version and X-App-Version identify the release. X-App-Instance is an opaque per-instance marker. These diagnostics contain text, unlike the homepage.
- Source, eight unit tests, buildspec.yml and tools/probe.py are in both ZIPs.
- Artwork generated with Microsoft Copilot. It is a stylized interpretation, not an architecturally exact representation.
- Locally tested, not deployed or tested in your AWS account. No cloud resources have been created.

## 1. Cost controls FIRST
The small app does not make AWS infrastructure free. Elastic Beanstalk has no additional service charge; you pay for its resources. [1]
- Create a small cost budget with email alerts. Alerts are NOT a hard spending cap and billing data can be delayed. [9]
- Use Standard / EC2-based Elastic Beanstalk, not EKS/Cluster mode, for this lab. [10]
- Suggested starting instance: t3.micro, x86_64, On-Demand. This is a recommendation, not a measured AWS memory guarantee. Choose a compatible small instance available in your Region.
- No RDS, Redis, NAT Gateway, custom domain or SSH key is needed by this app.
- For a temporary public lab, use public subnets, an internet gateway and public IPv4 on instances so package downloads work without NAT. This is not a private production design. Public IPv4, disks, traffic and logs can still cost money. Never store secrets or personal data in this demo.
- Leave detailed monitoring, tracing and persistent log streaming off unless intentionally testing them. Enable enhanced environment health.
- Terminate environments after your session. Stopping EC2 instances is not a substitute: Auto Scaling can replace them.
- Check regional EC2, EBS, public IPv4, ALB, S3, CodeBuild and CodePipeline rates. Do not assume Free Tier or credits apply. [1]

## 2. First deployment: MANUAL
For the cheapest first check, use a single-instance environment. If ready to test all policies immediately, skip this single-instance stage and manually deploy into the load-balanced environment in section 3 instead.

1. Elastic Beanstalk > Create application / Create environment.
2. Application: krakow-python. Environment: krakow-manual. Web server environment, Standard/EC2 mode if offered.
3. Platform: Python on a currently supported Amazon Linux 2023 branch. Select a supported Python 3 version, for example 3.12 if offered.
4. Upload your code: select krakow-v1.zip UNCHANGED. Version label: krakow-v1.
5. Environment type: Single instance. Suggested instance: t3.micro, On-Demand.
6. Service access: select/create BOTH the Elastic Beanstalk service role and EC2 instance profile. They are different roles. Follow the wizard's IAM guidance if missing; do not grant AdministratorAccess as a workaround. [8]
7. Networking: VPC with a public instance subnet, public IPv4 enabled, no database. Permit required HTTP for the public demo; no SSH is needed.
8. Review resources, submit and wait for Ready/healthy.
9. Open the environment URL: artwork and teal background, no visible text.
10. Open URL/health: expect HTTP 200 and status ok. Open URL/version: expect v1.
11. Choose Upload and deploy > krakow-v2.zip > version label krakow-v2. Refresh: orange background. Manual upload/redeploy instructions: [2].

ZIP files already have application.py, requirements.txt and Procfile at their ROOT. Do not wrap them in another ZIP or add a parent folder. [4]

Optional local preview after extracting either ZIP into an empty directory:
```bash
python application.py
```
Open http://127.0.0.1:8000. No package installation is required for this standard-library preview. AWS uses Gunicorn from Procfile, on port 8000. [5]

## 3. Environment for ALL deployment policies
There are FIVE policies: All at once, Rolling, Rolling with additional batch, Immutable and Traffic splitting. Blue/green is a separate two-environment workflow, not a sixth dropdown policy. Rolling policies require load balancing; traffic splitting specifically requires an Application Load Balancer. Immutable also works with single-instance environments. [2][3]

Create a fresh environment under the SAME application for a clear setup:
- Name: krakow-strategies; same Python platform and instance type.
- Deploy existing krakow-v1, or upload the v1 ZIP.
- Environment type: Load balanced.
- Load balancer: dedicated Application Load Balancer (ALB). Choose this during creation: its type cannot be changed in place later. [6]
- Public ALB subnets in TWO Availability Zones.
- Public instance subnets with public IPv4, internet access, no NAT for this temporary lab.
- Auto Scaling minimum 2, maximum 2. This holds a two-instance baseline for clear rolling observations; it does NOT test demand-based autoscaling.
- HTTP listener 80. Keep default backend process on HTTP port 80, which reaches the instance proxy. Gunicorn stays on 8000 behind that proxy. Do NOT change the default process port to 8000. [5][6]
- Load balancer settings > Processes > default > health check path /health; success code 200. ALB health checks use the PROCESS path, not a separate generic application health URL. [6]
- No session stickiness. Enhanced health enabled. Ignore health check disabled.
- Public HTTP to ALB; instance HTTP allowed from ALB security group rather than the whole internet. No SSH needed.

Wait for BOTH instances and ALB targets to become healthy. Check /health and /version. Then terminate krakow-manual if created. The overlap temporarily bills both environments.

## 4. Test all five policies
For EACH experiment:
1. Start with a healthy v1 or v2 baseline.
2. Select the policy; apply and wait for the configuration update to finish.
3. Start the observer in another terminal.
4. Upload and deploy the OTHER version.
5. Watch Events, Health, EC2 instance counts and ALB target groups.
6. Record results; wait for Ready/healthy and temporary-instance cleanup before the next experiment.

From the extracted source directory:
```bash
python tools/probe.py http://YOUR-ENVIRONMENT-URL --count 600
```
This observes YOUR lab at at most one small request per second, up to 600 requests. It is not a stress test and is not intended to trigger autoscaling. Restart it if the deployment takes longer. Output: UTC time, status, release, opaque instance marker and latency. It does not retain cookies. Small samples will not exactly match canary percentages; brief interruptions can be missed by one-second sampling.

Console policy location documented by AWS: environment > Configuration > Rolling updates and deployments / Updates and deployments > Application deployments > Deployment policy. Change the APPLICATION deployment policy, not the separate rolling configuration-update policy. Apply and wait for Ready. [3]

If the console groups settings differently, use CLI/CloudShell rather than guessing. Set your values:
```bash
export AWS_DEFAULT_REGION=YOUR_REGION
export ENV=krakow-strategies
```
Run ONE policy command, wait for Ready, THEN upload/deploy the other release:

### All at once
```bash
aws elasticbeanstalk update-environment --environment-name "$ENV" --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=AllAtOnce
```
Both instances update; temporary unavailability is possible. Planned baseline count: 2. [3]

### Rolling, batch 1
```bash
aws elasticbeanstalk update-environment --environment-name "$ENV" --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Rolling Namespace=aws:elasticbeanstalk:command,OptionName=BatchSizeType,Value=Fixed Namespace=aws:elasticbeanstalk:command,OptionName=BatchSize,Value=1
```
One instance updates while the other serves. Old/new versions can overlap. Planned count: 2. [3]

### Rolling with additional batch, batch 1
```bash
aws elasticbeanstalk update-environment --environment-name "$ENV" --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=RollingWithAdditionalBatch Namespace=aws:elasticbeanstalk:command,OptionName=BatchSizeType,Value=Fixed Namespace=aws:elasticbeanstalk:command,OptionName=BatchSize,Value=1
```
Extra instance launches before batches update. Planned temporary count: about 3. [3]

### Immutable
```bash
aws elasticbeanstalk update-environment --environment-name "$ENV" --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable
```
New group launches; old instances remain until health checks pass. Planned temporary count: up to about 4. [3]

### Traffic splitting: 10% canary, 3-minute evaluation
```bash
aws elasticbeanstalk update-environment --environment-name "$ENV" --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=TrafficSplitting Namespace=aws:elasticbeanstalk:trafficsplitting,OptionName=NewVersionPercent,Value=10 Namespace=aws:elasticbeanstalk:trafficsplitting,OptionName=EvaluationTime,Value=3
```
New group launches; roughly 10% of traffic goes to the new version during evaluation, then all traffic if healthy. Planned temporary count: about 4. [3]

IMPORTANT: These commands configure the policy; they do not themselves deploy a new application version. No policy .ebextensions file is bundled, so the source does not force a policy on every deployment.

Counts above are simplified planning examples, NOT measured results or hard caps. Failures/replacement activity can change them. Auto Scaling max 2 does NOT cap total temporary instances across deployment groups. Account quotas must permit extra capacity. [3]

Record: policy, old/new version, start/end time, HTTP errors, mixed-version responses, peak instance count and final health.

### Manual rollback
Applications > krakow-python > Application versions > select known-good krakow-v1 > Actions > Deploy > select environment. [2]

This lab tests successful deployments and manual rollback. It does NOT prove automatic failure rollback. No intentionally broken ZIP is included. Study failure injection later in an isolated disposable environment, with Ignore health check off. Rolling failures and immutable/traffic-splitting failures have different recovery behavior. [2][3]

## 5. Blue/green separately
1. Keep the existing environment as blue.
2. Create a second compatible environment as green with the other version.
3. For a cheaper separate exercise, use TWO single-instance environments instead of two load-balanced environments. Terminate the strategies environment first if no longer needed; do not accidentally keep all environments running.
4. Test green's own URL and /health.
5. Environment overview > Actions > Swap environment URLs > select the other environment > confirm.
6. Verify the original public URL now returns the new version. Roll back by swapping again if needed.
7. Wait for DNS caches to expire and traffic to move BEFORE terminating the old environment. A CNAME swap is not instantaneous for every client. [7]

Blue/green temporarily bills both environments. It is not a deployment-policy dropdown choice. [2][7]

## 6. THEN create GitHub/CodeCommit pipeline
Extract v1 into an empty directory. Commit the EXTRACTED FILES, not the ZIP and not an enclosing folder. application.py, release.json, requirements.txt, Procfile and buildspec.yml belong at repository root. [4]

### Cheapest simple automation
GitHub/CodeCommit source -> CodePipeline -> Elastic Beanstalk deploy.
Skip CodeBuild. Use the source ZIP artifact as deploy input. This automates deployment but does not run the bundled tests. Elastic Beanstalk installs requirements itself. [5][11]

### Learning pipeline with tests
GitHub/CodeCommit source -> CodeBuild tests/package -> Elastic Beanstalk deploy.
1. Create a custom pipeline; use one execution at a time, not parallel deployments to the same environment.
2. Source: GitHub via GitHub App/CodeConnections, authorize repository and select main. Use default ZIP artifact format, not Full clone for direct deployment. Or choose AWS CodeCommit with your repository/branch if available in your account. GitHub setup: [12].
3. Add CodeBuild in the pipeline build stage. Create the build project FROM WITHIN the pipeline flow so the pipeline supplies source. Do not select GitHub again as an independent build-project source.
4. Managed Linux build image with supported Python 3, small supported compute, no privileged mode and no VPC attachment. Use repository buildspec.yml. It installs requirements, runs eight tests and emits only deployable files.
5. Deploy provider: AWS Elastic Beanstalk. Select krakow-python and your CURRENT environment. Input: BuildArtifact (or your build output name), not SourceArtifact. [11]
6. Roles need scoped source/connection, S3 artifacts, logs and deployment permissions. Never put AWS keys in source or grant administrator access just to bypass a denial.
7. Commit/push; wait for Source, Build and Deploy to succeed. Check /version.
8. Edit release.json to the following, commit/push and observe orange background:
```json
{"version":"v2","theme":"orange","health_ok":true}
```
9. For policy tests through CI/CD, change the environment policy FIRST, wait for Ready, then push the next release. The pipeline transports the artifact; Beanstalk applies the policy. [3][11]

The native Beanstalk deploy action targets ONE named environment. It does not automatically create green or swap URLs. Keep blue/green manual in this lab. [7][11]

## 7. Cleanup EVERY session
- Wait for deployment completion or abort safely.
- Terminate ALL lab environments, including manual and blue/green. Verify deletion completes.
- Verify related lab EC2 instances, Auto Scaling groups, ALBs, target groups, disks and public/Elastic IP resources are gone. Never delete shared resources used elsewhere.
- Remove lab pipeline/build project when finished. Review retained application versions, S3 artifacts and CloudWatch logs; delete only unneeded lab data after checking it is not shared.
- Check Billing/Cost Explorer again after data updates. Retained storage/logs can still cost money. [1][9]

## Official AWS sources
[1] https://aws.amazon.com/elasticbeanstalk/pricing/
[2] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.deploy-existing-version.html
[3] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html
[4] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/applications-sourcebundle.html
[5] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/python-configuration-procfile.html
[6] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-cfg-alb.html
[7] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.CNAMESwap.html
[8] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts-roles.html
[9] https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
[10] https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html
[11] https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-Beanstalk.html
[12] https://docs.aws.amazon.com/codepipeline/latest/userguide/connections-github.html
