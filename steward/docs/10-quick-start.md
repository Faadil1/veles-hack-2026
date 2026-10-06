---
source: https://ide-tutorial.hyperai.di.uoa.gr/quick-start-demo/
title: Quick Start Demo
retrieved: 2026-10-06
fidelity: summarised by the fetch tool (not verbatim)
---
# Deploying your first application
## Step 0: Container registry
Your Docker image must be pushed to a public, whitelisted registry such as Docker Hub. Build locally with `docker build -t <user>/<image>:<tag> .` and push with `docker push <user>/<image>:<tag>`.
## Step 1: Sign in
Open the IDE at ide.hyperai.di.uoa.gr and sign in. New users can register on the same page.
## Step 2: Workspace
Create a working directory in the Workspace Explorer to organise your applications.
## Step 3: Application profile
Create a `.yaml` file that defines the application's attributes and references the container image from step 0. The format differs for Native Apps and Device Apps.
## Step 4: Deploy
Save the profile and click Deploy. Select the profiles to deploy in the dialog and optionally name the workflow.
## Step 5: Run
Open the Dashboard, find the deployment and click Start. The workflow moves to Running once initialisation completes. The Metrics button shows live analytics for active workflows.
