"""
Azure Container Apps Service for Hosted MCP Servers

This service handles deployment, lifecycle management, and monitoring
of MCP servers on Azure Container Apps.
"""
import logging
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from azure.identity import ClientSecretCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
from azure.mgmt.appcontainers.models import (
    ContainerApp,
    Configuration,
    Ingress,
    Template,
    Container,
    ContainerResources,
    Scale,
    ScaleRule,
    Secret,
    RegistryCredentials,
    ManagedEnvironment,
)
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ContainerAppConfig:
    """Configuration for creating a Container App."""
    name: str
    image: str
    port: int = 3000
    cpu_cores: float = 0.25
    memory_gb: float = 0.5
    min_replicas: int = 0
    max_replicas: int = 3
    environment_variables: Dict[str, str] = None
    secrets: List[Dict[str, str]] = None  # [{"name": "secret-name", "value": "secret-value"}]


@dataclass
class ContainerAppStatus:
    """Status of a Container App."""
    provisioning_state: str  # Succeeded, Failed, Canceled, InProgress
    running_status: str  # Running, Stopped, Unknown
    fqdn: Optional[str] = None
    resource_id: Optional[str] = None
    error_message: Optional[str] = None


class AzureContainerAppsService:
    """
    Service for managing Azure Container Apps for Hosted MCP Servers.

    Usage:
        service = AzureContainerAppsService()
        config = ContainerAppConfig(
            name="mcp-weather-abc123",
            image="ghcr.io/anthropic/mcp-weather:latest",
            port=3000,
        )
        await service.deploy_container_app(config)
    """

    def __init__(self):
        self._client: Optional[ContainerAppsAPIClient] = None
        self._environment_name: Optional[str] = None

    def _get_credential(self) -> ClientSecretCredential:
        """Get Azure credential from settings."""
        if not settings.AZURE_CLIENT_ID or not settings.AZURE_CLIENT_SECRET or not settings.AZURE_TENANT_ID:
            raise ValueError("Azure credentials not configured. Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID.")

        return ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
        )

    def _get_client(self) -> ContainerAppsAPIClient:
        """Get or create the Container Apps API client."""
        if self._client is None:
            if not settings.AZURE_SUBSCRIPTION_ID:
                raise ValueError("Azure subscription ID not configured. Please set AZURE_SUBSCRIPTION_ID.")

            credential = self._get_credential()
            self._client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=settings.AZURE_SUBSCRIPTION_ID,
            )
        return self._client

    async def get_environment_name(self) -> str:
        """
        Get the Container Apps environment name.
        Discovers the first environment in the resource group.
        """
        if self._environment_name:
            return self._environment_name

        try:
            client = self._get_client()
            environments = list(client.managed_environments.list_by_resource_group(
                resource_group_name=settings.AZURE_RESOURCE_GROUP
            ))

            if not environments:
                raise ValueError(f"No Container Apps environment found in resource group {settings.AZURE_RESOURCE_GROUP}")

            self._environment_name = environments[0].name
            logger.info(f"Using Container Apps environment: {self._environment_name}")
            return self._environment_name
        except Exception as e:
            logger.error(f"Failed to get Container Apps environment: {e}")
            raise

    def generate_app_name(self, base_name: str, organization_id: str) -> str:
        """
        Generate a unique Container App name.

        Format: mcp-{base_name}-{short_uuid}
        Must be lowercase, alphanumeric with hyphens, max 63 chars.
        """
        # Clean base name
        clean_name = base_name.lower().replace(' ', '-').replace('_', '-')
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')
        clean_name = clean_name[:30]  # Limit to leave room for prefix and suffix

        # Generate short unique suffix
        short_uuid = str(uuid.uuid4())[:8]

        # Create app name
        app_name = f"mcp-{clean_name}-{short_uuid}"

        # Ensure valid format (max 63 chars, no leading/trailing hyphens)
        app_name = app_name.strip('-')[:63]

        return app_name

    async def deploy_container_app(self, config: ContainerAppConfig) -> ContainerAppStatus:
        """
        Deploy a new Container App.

        Args:
            config: ContainerAppConfig with deployment settings

        Returns:
            ContainerAppStatus with deployment result
        """
        try:
            client = self._get_client()
            environment_name = await self.get_environment_name()

            # Get environment resource ID
            environment = client.managed_environments.get(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                environment_name=environment_name,
            )

            # Build secrets list
            secrets = []
            secret_refs = {}
            if config.secrets:
                for secret in config.secrets:
                    secrets.append(Secret(name=secret["name"], value=secret["value"]))
                    secret_refs[secret["name"]] = secret["name"]

            # Add ACR credentials as secrets if using private registry
            if settings.ACR_LOGIN_SERVER and settings.ACR_PASSWORD:
                secrets.append(Secret(name="acr-password", value=settings.ACR_PASSWORD))

            # Build environment variables
            env_vars = []
            if config.environment_variables:
                for key, value in config.environment_variables.items():
                    if value.startswith("secretref:"):
                        # Reference a secret
                        secret_name = value.replace("secretref:", "")
                        env_vars.append({"name": key, "secretRef": secret_name})
                    else:
                        env_vars.append({"name": key, "value": value})

            # Create container app definition
            container_app = ContainerApp(
                location=environment.location,
                managed_environment_id=environment.id,
                configuration=Configuration(
                    secrets=secrets if secrets else None,
                    ingress=Ingress(
                        external=False,  # Internal only
                        target_port=config.port,
                        transport="auto",
                        allow_insecure=False,
                    ),
                    registries=[
                        RegistryCredentials(
                            server=settings.ACR_LOGIN_SERVER,
                            username=settings.ACR_USERNAME,
                            password_secret_ref="acr-password",
                        )
                    ] if settings.ACR_LOGIN_SERVER and settings.ACR_USERNAME else None,
                ),
                template=Template(
                    containers=[
                        Container(
                            name="mcp-server",
                            image=config.image,
                            resources=ContainerResources(
                                cpu=config.cpu_cores,
                                memory=f"{config.memory_gb}Gi",
                            ),
                            env=env_vars if env_vars else None,
                        )
                    ],
                    scale=Scale(
                        min_replicas=config.min_replicas,
                        max_replicas=config.max_replicas,
                        rules=[
                            ScaleRule(
                                name="http-rule",
                                http={"metadata": {"concurrentRequests": "10"}},
                            )
                        ] if config.max_replicas > 0 else None,
                    ),
                ),
            )

            # Create the container app
            logger.info(f"Creating Container App: {config.name}")
            poller = client.container_apps.begin_create_or_update(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=config.name,
                container_app_envelope=container_app,
            )

            # Wait for completion
            result = poller.result()

            # Get the internal URL
            fqdn = None
            if result.configuration and result.configuration.ingress:
                fqdn = result.configuration.ingress.fqdn

            logger.info(f"Container App created: {config.name}, FQDN: {fqdn}")

            return ContainerAppStatus(
                provisioning_state=result.provisioning_state,
                running_status=result.properties.running_status if hasattr(result, 'properties') else "Unknown",
                fqdn=fqdn,
                resource_id=result.id,
            )

        except HttpResponseError as e:
            logger.error(f"Azure API error deploying container app: {e}")
            return ContainerAppStatus(
                provisioning_state="Failed",
                running_status="Unknown",
                error_message=str(e),
            )
        except Exception as e:
            logger.error(f"Error deploying container app: {e}")
            return ContainerAppStatus(
                provisioning_state="Failed",
                running_status="Unknown",
                error_message=str(e),
            )

    async def delete_container_app(self, app_name: str) -> bool:
        """
        Delete a Container App.

        Args:
            app_name: Name of the Container App to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            client = self._get_client()

            logger.info(f"Deleting Container App: {app_name}")
            poller = client.container_apps.begin_delete(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
            )
            poller.result()

            logger.info(f"Container App deleted: {app_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Container App not found: {app_name}")
            return True  # Already deleted
        except Exception as e:
            logger.error(f"Error deleting container app: {e}")
            return False

    async def start_container_app(self, app_name: str, min_replicas: int = 1) -> ContainerAppStatus:
        """
        Start a stopped Container App by scaling up.

        Args:
            app_name: Name of the Container App
            min_replicas: Minimum replicas to scale to

        Returns:
            ContainerAppStatus with result
        """
        try:
            client = self._get_client()

            # Get current app
            app = client.container_apps.get(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
            )

            # Update scale settings
            if app.template and app.template.scale:
                app.template.scale.min_replicas = min_replicas

            # Update the app
            logger.info(f"Starting Container App: {app_name} (min_replicas={min_replicas})")
            poller = client.container_apps.begin_create_or_update(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
                container_app_envelope=app,
            )
            result = poller.result()

            return ContainerAppStatus(
                provisioning_state=result.provisioning_state,
                running_status="Running",
                fqdn=result.configuration.ingress.fqdn if result.configuration and result.configuration.ingress else None,
                resource_id=result.id,
            )

        except Exception as e:
            logger.error(f"Error starting container app: {e}")
            return ContainerAppStatus(
                provisioning_state="Failed",
                running_status="Unknown",
                error_message=str(e),
            )

    async def stop_container_app(self, app_name: str) -> ContainerAppStatus:
        """
        Stop a Container App by scaling to zero.

        Args:
            app_name: Name of the Container App

        Returns:
            ContainerAppStatus with result
        """
        try:
            client = self._get_client()

            # Get current app
            app = client.container_apps.get(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
            )

            # Update scale settings to zero
            if app.template and app.template.scale:
                app.template.scale.min_replicas = 0
                app.template.scale.max_replicas = 0

            # Update the app
            logger.info(f"Stopping Container App: {app_name}")
            poller = client.container_apps.begin_create_or_update(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
                container_app_envelope=app,
            )
            result = poller.result()

            return ContainerAppStatus(
                provisioning_state=result.provisioning_state,
                running_status="Stopped",
                fqdn=result.configuration.ingress.fqdn if result.configuration and result.configuration.ingress else None,
                resource_id=result.id,
            )

        except Exception as e:
            logger.error(f"Error stopping container app: {e}")
            return ContainerAppStatus(
                provisioning_state="Failed",
                running_status="Unknown",
                error_message=str(e),
            )

    async def get_container_status(self, app_name: str) -> ContainerAppStatus:
        """
        Get the current status of a Container App.

        Args:
            app_name: Name of the Container App

        Returns:
            ContainerAppStatus with current state
        """
        try:
            client = self._get_client()

            app = client.container_apps.get(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
            )

            # Determine running status based on replicas
            running_status = "Unknown"
            if app.template and app.template.scale:
                if app.template.scale.max_replicas == 0:
                    running_status = "Stopped"
                elif app.provisioning_state == "Succeeded":
                    running_status = "Running"

            return ContainerAppStatus(
                provisioning_state=app.provisioning_state,
                running_status=running_status,
                fqdn=app.configuration.ingress.fqdn if app.configuration and app.configuration.ingress else None,
                resource_id=app.id,
            )

        except ResourceNotFoundError:
            return ContainerAppStatus(
                provisioning_state="NotFound",
                running_status="Deleted",
                error_message="Container App not found",
            )
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return ContainerAppStatus(
                provisioning_state="Unknown",
                running_status="Unknown",
                error_message=str(e),
            )

    async def get_container_logs(self, app_name: str, lines: int = 100) -> str:
        """
        Get container logs for a Container App.

        Note: Container Apps logs are available via Azure Monitor/Log Analytics.
        This method provides a simplified approach using the management API.

        Args:
            app_name: Name of the Container App
            lines: Number of log lines to retrieve

        Returns:
            Log content as string
        """
        try:
            # Note: Full log retrieval requires Log Analytics integration
            # This is a placeholder that returns status info
            status = await self.get_container_status(app_name)

            log_content = f"""
=== Container App: {app_name} ===
Provisioning State: {status.provisioning_state}
Running Status: {status.running_status}
FQDN: {status.fqdn or 'N/A'}
Resource ID: {status.resource_id or 'N/A'}

Note: Full container logs are available via Azure Portal > Container Apps > {app_name} > Logs
or via Azure CLI: az containerapp logs show --name {app_name} --resource-group {settings.AZURE_RESOURCE_GROUP}
"""

            if status.error_message:
                log_content += f"\nError: {status.error_message}"

            return log_content.strip()

        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            return f"Error retrieving logs: {str(e)}"

    async def redeploy_container_app(self, app_name: str, new_image: Optional[str] = None) -> ContainerAppStatus:
        """
        Redeploy a Container App with optional new image.

        Args:
            app_name: Name of the Container App
            new_image: Optional new image to deploy

        Returns:
            ContainerAppStatus with result
        """
        try:
            client = self._get_client()

            # Get current app
            app = client.container_apps.get(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
            )

            # Update image if provided
            if new_image and app.template and app.template.containers:
                app.template.containers[0].image = new_image

            # Force a new revision by updating a label
            if not app.template.revision_suffix:
                app.template.revision_suffix = f"r{uuid.uuid4().hex[:8]}"
            else:
                app.template.revision_suffix = f"r{uuid.uuid4().hex[:8]}"

            # Update the app
            logger.info(f"Redeploying Container App: {app_name}")
            poller = client.container_apps.begin_create_or_update(
                resource_group_name=settings.AZURE_RESOURCE_GROUP,
                container_app_name=app_name,
                container_app_envelope=app,
            )
            result = poller.result()

            return ContainerAppStatus(
                provisioning_state=result.provisioning_state,
                running_status="Running",
                fqdn=result.configuration.ingress.fqdn if result.configuration and result.configuration.ingress else None,
                resource_id=result.id,
            )

        except Exception as e:
            logger.error(f"Error redeploying container app: {e}")
            return ContainerAppStatus(
                provisioning_state="Failed",
                running_status="Unknown",
                error_message=str(e),
            )


# Singleton instance
azure_container_apps_service = AzureContainerAppsService()
