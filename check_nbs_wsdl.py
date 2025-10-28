"""Check NBS WSDL to understand required parameters."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from zeep import Client
from app import create_app

app = create_app()

with app.app_context():
    print("Fetching NBS WSDL...")
    wsdl = "https://webservices.nbs.rs/CommunicationOfficeService1_0/CurrentExchangeRateXmlService.asmx?WSDL"
    client = Client(wsdl)

    print("\nAvailable operations:")
    print("=" * 60)
    for service in client.wsdl.services.values():
        for port in service.ports.values():
            operations = port.binding._operations.values()
            for operation in operations:
                print(f"\nOperation: {operation.name}")
                print(f"  Input: {operation.input}")
                if hasattr(operation.input.body, 'type'):
                    print(f"  Type: {operation.input.body.type}")
