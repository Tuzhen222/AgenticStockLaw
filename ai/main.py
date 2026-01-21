"""
Main entry point - Run AI services.

Usage:
    python -m ai.main              # Run all services
    python -m ai.main gateway      # Run only AI Gateway (9200)
    python -m ai.main orchestrator # Run only orchestrator
    python -m ai.main knowledge    # Run only knowledge agent
"""
import os
import sys
import logging
import subprocess
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment  
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Import config
from ai.config import ALL_SERVICES, GATEWAY_PORT


def run_single_service(service_name: str):
    """Run a single service."""
    if service_name not in ALL_SERVICES:
        print(f"Unknown service: {service_name}")
        print(f"Available: {', '.join(ALL_SERVICES.keys())}")
        sys.exit(1)
    
    service = ALL_SERVICES[service_name]
    logger.info(f"Starting {service['name']} on port {service['port']}")
    
    if service_name == "gateway":
        from ai.gateway import run_gateway
        run_gateway()
    elif service_name == "orchestrator":
        from ai.agents.orchestrator.executor import build_app
        import uvicorn
        app = build_app()
        uvicorn.run(app.build(), host="0.0.0.0", port=service['port'])
    elif service_name == "knowledge":
        from ai.agents.knowledge.executor import build_app
        import uvicorn
        app = build_app()
        uvicorn.run(app.build(), host="0.0.0.0", port=service['port'])
    else:
        # Generic module run
        subprocess.run([
            sys.executable, "-m", service['module'],
            *service.get('args', [])
        ])


def run_all_services():
    """Run all services (for development)."""
    logger.info("Starting all AI services...")
    logger.info("Use Ctrl+C to stop all services")
    
    # For now, just run gateway - other services should be run separately or via docker-compose
    from ai.gateway import run_gateway
    run_gateway()


def print_help():
    """Print help message."""
    print(__doc__)
    print("\nAvailable services:")
    for name, config in ALL_SERVICES.items():
        print(f"  {name:15} - {config['name']} (port {config['port']})")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ["--help", "-h"]:
            print_help()
        elif arg in ALL_SERVICES:
            run_single_service(arg)
        else:
            print(f"Unknown service: {arg}")
            print(f"Available: {', '.join(ALL_SERVICES.keys())}")
            sys.exit(1)
    else:
        run_all_services()


if __name__ == "__main__":
    main()
