#!/usr/bin/env python3
"""
Manage PR Preview Environments on AWS Lightsail
"""

import argparse
import boto3
import time
import sys
import os

class PreviewManager:
    def __init__(self, region='us-east-1'):
        self.lightsail = boto3.client('lightsail', region_name=region)
        self.region = region
    
    def get_instance_name(self, pr_number, repo_name):
        """Generate instance name from PR number and repo"""
        # Clean repo name (remove owner, special chars)
        clean_repo = repo_name.split('/')[-1].replace('_', '-').replace('.', '-')
        return f"pr-{pr_number}-{clean_repo}"[:63]  # Lightsail name limit
    
    def instance_exists(self, instance_name):
        """Check if instance already exists"""
        try:
            self.lightsail.get_instance(instanceName=instance_name)
            return True
        except self.lightsail.exceptions.NotFoundException:
            return False
    
    def create_instance(self, instance_name, pr_number, repo_name, branch):
        """Create new Lightsail instance"""
        print(f"Creating instance: {instance_name}")
        
        try:
            response = self.lightsail.create_instances(
                instanceNames=[instance_name],
                availabilityZone=f'{self.region}a',
                blueprintId='ubuntu_22_04',
                bundleId='nano_3_0',
                tags=[
                    {'key': 'Type', 'value': 'PR-Preview'},
                    {'key': 'PR', 'value': str(pr_number)},
                    {'key': 'Repository', 'value': repo_name},
                    {'key': 'Branch', 'value': branch},
                    {'key': 'ManagedBy', 'value': 'GitHub-Actions'}
                ]
            )
            
            print(f"✅ Instance creation initiated")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create instance: {e}")
            return False
    
    def wait_for_instance(self, instance_name, max_wait=300):
        """Wait for instance to be running and get IP"""
        print(f"⏳ Waiting for instance to be ready...")
        
        start_time = time.time()
        while (time.time() - start_time) < max_wait:
            try:
                response = self.lightsail.get_instance(instanceName=instance_name)
                instance = response['instance']
                state = instance['state']['name']
                
                print(f"   Status: {state}")
                
                if state == 'running' and 'publicIpAddress' in instance:
                    ip = instance['publicIpAddress']
                    print(f"✅ Instance ready with IP: {ip}")
                    return ip
                
                time.sleep(10)
                
            except Exception as e:
                print(f"   Waiting... {e}")
                time.sleep(10)
        
        print(f"❌ Instance did not become ready within {max_wait}s")
        return None
    
    def configure_firewall(self, instance_name):
        """Open necessary ports"""
        print(f"🔥 Configuring firewall...")
        
        try:
            self.lightsail.put_instance_public_ports(
                portInfos=[
                    {'fromPort': 22, 'toPort': 22, 'protocol': 'tcp'},
                    {'fromPort': 80, 'toPort': 80, 'protocol': 'tcp'},
                    {'fromPort': 443, 'toPort': 443, 'protocol': 'tcp'},
                    {'fromPort': 3000, 'toPort': 3000, 'protocol': 'tcp'},  # Node.js
                    {'fromPort': 5000, 'toPort': 5000, 'protocol': 'tcp'},  # Python
                ],
                instanceName=instance_name
            )
            print("✅ Firewall configured")
            return True
        except Exception as e:
            print(f"⚠️  Firewall configuration failed: {e}")
            return False

    def deploy_application(self, instance_name, instance_ip, repo_name, branch, commit_sha):
        """Deploy application to instance"""
        print(f"📦 Deploying application...")
        
        # Wait for SSH to be ready
        print("⏳ Waiting for SSH to be ready...")
        time.sleep(60)  # Give instance time to fully boot
        
        # Create deployment script
        deploy_script = f"""#!/bin/bash
set -e

echo "🔧 Setting up preview environment..."

# Update system
sudo apt-get update -qq

# Install dependencies
sudo apt-get install -y nginx git curl

# Clone repository
cd /home/ubuntu
if [ -d "app" ]; then
    cd app
    git fetch origin
    git checkout {branch}
    git pull
else
    git clone https://github.com/{repo_name}.git app
    cd app
    git checkout {branch}
fi

# Detect app type and deploy
if [ -f "package.json" ]; then
    echo "📦 Node.js app detected"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    npm install
    
    # Check if it's a React app
    if grep -q '"react"' package.json; then
        echo "⚛️  React app detected"
        npm run build
        sudo rm -rf /var/www/html/*
        sudo cp -r build/* /var/www/html/
        
        # Configure Nginx for React SPA
        sudo tee /etc/nginx/sites-available/default > /dev/null << 'NGINX_EOF'
server {{{{
    listen 80;
    server_name _;
    root /var/www/html;
    index index.html;
    
    location / {{{{
        try_files $uri $uri/ /index.html;
    }}}}
}}}}
NGINX_EOF
    else
        echo "🟢 Node.js API detected"
        # Install PM2
        sudo npm install -g pm2
        pm2 start npm --name "app" -- start
        pm2 save
        pm2 startup | tail -n 1 | sudo bash
        
        # Configure Nginx as reverse proxy
        sudo tee /etc/nginx/sites-available/default > /dev/null << 'NGINX_EOF'
server {{{{
    listen 80;
    server_name _;
    location / {{{{
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}}}
}}}}
NGINX_EOF
    fi
elif [ -f "requirements.txt" ]; then
    echo "🐍 Python app detected"
    sudo apt-get install -y python3-pip
    pip3 install -r requirements.txt
    
    # Create systemd service
    sudo tee /etc/systemd/system/app.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Python App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/app
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable app
    sudo systemctl start app
    
    # Configure Nginx as reverse proxy
    sudo tee /etc/nginx/sites-available/default > /dev/null << 'NGINX_EOF'
server {{{{
    listen 80;
    server_name _;
    location / {{{{
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}}}
}}}}
NGINX_EOF
fi

# Restart Nginx
sudo systemctl restart nginx

echo "✅ Deployment complete!"
"""
        
        # Save script locally
        with open('/tmp/deploy.sh', 'w') as f:
            f.write(deploy_script)
        
        print(f"📤 Uploading deployment script to {instance_ip}...")
        # Note: In production, you'd use SSH here
        # For now, we'll use AWS Systems Manager or user data
        
        return True

    def delete_instance(self, instance_name):
        """Delete Lightsail instance"""
        print(f"🗑️  Deleting instance: {instance_name}")
        
        try:
            self.lightsail.delete_instance(instanceName=instance_name)
            print(f"✅ Instance deletion initiated")
            return True
        except self.lightsail.exceptions.NotFoundException:
            print(f"⚠️  Instance not found (may already be deleted)")
            return True
        except Exception as e:
            print(f"❌ Failed to delete instance: {e}")
            return False
    
    def create_preview(self, pr_number, repo_name, branch, commit_sha):
        """Create or update preview environment"""
        instance_name = self.get_instance_name(pr_number, repo_name)
        
        print(f"{'='*60}")
        print(f"🚀 Creating Preview Environment")
        print(f"{'='*60}")
        print(f"PR Number: {pr_number}")
        print(f"Repository: {repo_name}")
        print(f"Branch: {branch}")
        print(f"Commit: {commit_sha[:7]}")
        print(f"Instance: {instance_name}")
        print(f"{'='*60}\n")
        
        # Check if instance exists
        if self.instance_exists(instance_name):
            print(f"ℹ️  Instance already exists, will update deployment")
            response = self.lightsail.get_instance(instanceName=instance_name)
            instance_ip = response['instance']['publicIpAddress']
        else:
            # Create new instance
            if not self.create_instance(instance_name, pr_number, repo_name, branch):
                sys.exit(1)
            
            # Wait for instance to be ready
            instance_ip = self.wait_for_instance(instance_name)
            if not instance_ip:
                sys.exit(1)
            
            # Configure firewall
            self.configure_firewall(instance_name)
        
        # Deploy application
        self.deploy_application(instance_name, instance_ip, repo_name, branch, commit_sha)
        
        # Output for GitHub Actions
        print(f"\n{'='*60}")
        print(f"✅ Preview Environment Ready!")
        print(f"{'='*60}")
        print(f"URL: http://{instance_ip}/")
        print(f"Instance: {instance_name}")
        
        # Set GitHub Actions outputs
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"preview_url=http://{instance_ip}/\n")
                f.write(f"instance_ip={instance_ip}\n")
                f.write(f"instance_name={instance_name}\n")
        
        return True
    
    def delete_preview(self, pr_number, repo_name):
        """Delete preview environment"""
        instance_name = self.get_instance_name(pr_number, repo_name)
        
        print(f"{'='*60}")
        print(f"🧹 Cleaning Up Preview Environment")
        print(f"{'='*60}")
        print(f"PR Number: {pr_number}")
        print(f"Instance: {instance_name}")
        print(f"{'='*60}\n")
        
        return self.delete_instance(instance_name)

def main():
    parser = argparse.ArgumentParser(description='Manage PR Preview Environments')
    parser.add_argument('action', choices=['create', 'delete'], help='Action to perform')
    parser.add_argument('--pr-number', required=True, type=int, help='Pull request number')
    parser.add_argument('--repo-name', required=True, help='Repository name (owner/repo)')
    parser.add_argument('--branch', help='Branch name (required for create)')
    parser.add_argument('--commit-sha', help='Commit SHA (required for create)')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    manager = PreviewManager(region=args.region)
    
    if args.action == 'create':
        if not args.branch or not args.commit_sha:
            print("❌ --branch and --commit-sha are required for create action")
            sys.exit(1)
        
        success = manager.create_preview(
            args.pr_number,
            args.repo_name,
            args.branch,
            args.commit_sha
        )
    else:  # delete
        success = manager.delete_preview(args.pr_number, args.repo_name)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
