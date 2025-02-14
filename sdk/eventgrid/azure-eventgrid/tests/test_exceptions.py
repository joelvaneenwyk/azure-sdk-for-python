#-------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#--------------------------------------------------------------------------

import logging
import sys
import os
import json
import pytest
import uuid
from datetime import datetime, timedelta
from azure.core.exceptions import (
    HttpResponseError,
    ClientAuthenticationError,
    ServiceRequestError
)
from msrest.serialization import UTC
import datetime as dt

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from devtools_testutils import AzureMgmtRecordedTestCase, recorded_by_proxy

from azure_devtools.scenario_tests import ReplayableTest
from azure.core.credentials import AzureKeyCredential, AzureSasCredential
from azure.core.messaging import CloudEvent
from azure.core.serialization import NULL
from azure.eventgrid import EventGridPublisherClient, EventGridEvent, generate_sas
from azure.eventgrid._helpers import _cloud_event_to_generated

from eventgrid_preparer import (
    EventGridPreparer,
)

class TestEventGridPublisherClientExceptions(AzureMgmtRecordedTestCase):
    def create_eg_publisher_client(self, endpoint):
        credential = self.get_credential(EventGridPublisherClient)
        client = self.create_client_from_credential(EventGridPublisherClient, credential=credential, endpoint=endpoint)
        return client

    @EventGridPreparer()
    @recorded_by_proxy
    def test_raise_on_auth_error(self, eventgrid_topic_endpoint):
        akc_credential = AzureKeyCredential("bad credential")
        client = EventGridPublisherClient(eventgrid_topic_endpoint, akc_credential)
        eg_event = EventGridEvent(
                subject="sample", 
                data={"sample": "eventgridevent"}, 
                event_type="Sample.EventGrid.Event",
                data_version="2.0"
                )
        with pytest.raises(ClientAuthenticationError, match="The request authorization key is not authorized for*"):
            client.send(eg_event)

    @pytest.mark.live_test_only
    @EventGridPreparer()
    def test_raise_on_bad_resource(self, eventgrid_topic_key):
        akc_credential = AzureKeyCredential(eventgrid_topic_key)
        client = EventGridPublisherClient("https://bad-resource.westus-1.eventgrid.azure.net/api/events", akc_credential)
        eg_event = EventGridEvent(
                subject="sample", 
                data={"sample": "eventgridevent"}, 
                event_type="Sample.EventGrid.Event",
                data_version="2.0"
                )
        with pytest.raises(HttpResponseError):
            client.send(eg_event)

    @EventGridPreparer()
    @recorded_by_proxy
    def test_raise_on_large_payload(self, eventgrid_topic_endpoint):
        client = self.create_eg_publisher_client(eventgrid_topic_endpoint)

        path  = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", "./large_data.json"))
        with open(path) as json_file:
            data = json.load(json_file)
        eg_event = EventGridEvent(
                subject="sample", 
                data=data,
                event_type="Sample.EventGrid.Event",
                data_version="2.0"
                )
        with pytest.raises(HttpResponseError) as err:
            client.send(eg_event)
        assert "The maximum size (1536000) has been exceeded." in err.value.message
