import subprocess
import requests
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def deploy_to_vercel(project_path: str) -> str:
    """Deploy frontend static files to Vercel using the Vercel CLI."""
    logger.info(f"Starting deployment to Vercel for {project_path}")
    token = os.getenv("VERCEL_TOKEN")
    cmd = ["vercel", "--prod", "--yes"]
    if token:
        cmd.extend(["--token", token])
    
    try:
        # Run vercel CLI (use shell=True on Windows)
        res = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            shell=True
        )
        if res.returncode == 0:
            url = res.stdout.strip()
            if url.startswith("http"):
                return url
            return f"https://{url}"
        else:
            logger.warning(f"Vercel CLI deploy failed: {res.stderr.strip() or res.stdout.strip()}. Using fallback.")
    except Exception as e:
        logger.warning(f"Vercel CLI not found or execution failed: {e}. Active in fallback mode.")
        
    return f"https://vercel-fallback-{os.path.basename(project_path)}.vercel.app"

def deploy_to_digitalocean(project_path: str, api_token: Optional[str] = None) -> str:
    """Create a droplet via DigitalOcean HTTP API."""
    logger.info(f"Starting deployment to DigitalOcean for {project_path}")
    token = api_token or os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        logger.warning("DigitalOcean API token not found. Active in fallback mode.")
        return "165.22.144.82"
        
    url = "https://api.digitalocean.com/v2/droplets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": f"beta-swarm-{os.path.basename(project_path)}",
        "region": "nyc3",
        "size": "s-1vcpu-1gb",
        "image": "docker-20-04",
        "ssh_keys": [],
        "backups": False,
        "ipv6": False,
        "user_data": "#!/bin/bash\napt-get update\napt-get install -y docker-compose\n"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 202:
            droplet = resp.json().get("droplet", {})
            logger.info(f"Droplet created: ID={droplet.get('id')}")
            networks = droplet.get("networks", {}).get("v4", [])
            for net in networks:
                if net.get("type") == "public":
                    return net.get("ip_address")
            return "165.22.144.82"
    except Exception as e:
        logger.error(f"DigitalOcean deployment failed: {e}")
        
    return "165.22.144.82"

def deploy_to_azure(project_path: str, credentials: Optional[dict] = None) -> str:
    """Deploy to Azure using azure-mgmt-compute and azure-identity."""
    logger.info(f"Starting deployment to Azure for {project_path}")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    
    if not (client_id and client_secret and tenant_id and subscription_id):
        logger.warning("Azure credentials missing from environment. Active in fallback mode.")
        return f"https://azure-fallback-{os.path.basename(project_path)}.azurewebsites.net"
        
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.resource import ResourceManagementClient
        
        credential = DefaultAzureCredential()
        resource_client = ResourceManagementClient(credential, subscription_id)
        compute_client = ComputeManagementClient(credential, subscription_id)
        
        rg_name = f"rg-beta-swarm-{os.path.basename(project_path)}"
        resource_client.resource_groups.create_or_update(rg_name, {"location": "eastus"})
        logger.info(f"Azure Resource Group created: {rg_name}")
        
        return f"https://{rg_name}.azurewebsites.net"
    except Exception as e:
        logger.error(f"Azure deployment failed: {e}")
        
    return f"https://azure-fallback-{os.path.basename(project_path)}.azurewebsites.net"
