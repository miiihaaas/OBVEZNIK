"""Inspect actual NBS XML response."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from zeep import Client
from zeep import xsd
from zeep.transports import Transport

app = create_app()

with app.app_context():
    print("Calling NBS API and inspecting response...")
    print("=" * 60)

    wsdl = "https://webservices.nbs.rs/CommunicationOfficeService1_0/CurrentExchangeRateXmlService.asmx?WSDL"
    transport = Transport(timeout=10)
    client = Client(wsdl, transport=transport)

    # Create auth header
    namespace = "http://communicationoffice.nbs.rs"
    auth_header = xsd.Element(
        f'{{{namespace}}}AuthenticationHeader',
        xsd.ComplexType([
            xsd.Element(f'{{{namespace}}}UserName', xsd.String()),
            xsd.Element(f'{{{namespace}}}Password', xsd.String()),
            xsd.Element(f'{{{namespace}}}LicenceID', xsd.String()),
        ])
    )
    auth_value = auth_header(
        UserName=app.config['NBS_USERNAME'],
        Password=app.config['NBS_PASSWORD'],
        LicenceID=app.config['NBS_LICENCE_ID']
    )

    try:
        # Call API
        xml_response = client.service.GetCurrentExchangeRate(
            exchangeRateListTypeID=3,
            _soapheaders=[auth_value]
        )

        # Save XML to file
        with open('nbs_response.xml', 'w', encoding='utf-8') as f:
            f.write(xml_response)
        print("\n[OK] XML response saved to nbs_response.xml")

        # Try to parse and see structure
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_response)

        print("\nXML Root Tag:")
        print(f"  {root.tag}")

        print("\nFirst 10 child elements:")
        for i, child in enumerate(root):
            if i >= 10:
                break
            print(f"  {child.tag}: {child.text[:50] if child.text else 'None'}")

        print("\nSearching for exchange rate elements...")
        # Try different possible paths
        for pattern in ['.//ExchangeRate', './/*Rate*', './/*Currency*', './/*']:
            elements = root.findall(pattern)
            if elements:
                print(f"\nFound {len(elements)} elements matching '{pattern}'")
                if len(elements) > 0:
                    print(f"  First element: {elements[0].tag}")
                    for child in elements[0]:
                        print(f"    - {child.tag}: {child.text}")
                break

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
