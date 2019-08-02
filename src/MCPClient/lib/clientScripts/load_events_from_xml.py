from __future__ import absolute_import, unicode_literals

import logging
import os

from lxml import etree

import django

django.setup()  # NOQA
from django.db import transaction
from django.utils import dateparse
import metsrw
from main.models import Agent, Event, File

logger = logging.getLogger(__name__)


class LoadEventsFromXMLException(Exception):
    """Exception to raise if PREMIS validation fails."""


def parse_events_xml(xml_path, file_queryset):
    root = etree.parse(xml_path)
    return []


def call(jobs):
    for job in jobs:
        with job.JobContext(logger=logger):
            transfer_uuid = job.args[1]
            premis_xsd = job.args[2]
            xml_path = job.args[3]
            logger.debug(transfer_uuid, premis_xsd, xml_path)
            if not os.path.isfile(premis_xsd):
                msg = "The PREMIS XML schema asset ({}) is unavailable".format(
                    premis_xsd
                )
                raise LoadEventsFromXMLException(msg)
            try:
                xmlschema = etree.XMLSchema(etree.parse(premis_xsd))
            except etree.XMLSyntaxError as e:
                job.pyprint("Couldn't parse the PREMIS XML schema", premis_xsd)
                raise e
            if os.path.isfile(xml_path):
                try:
                    xmlschema.assertValid(etree.parse(xml_path))
                except etree.XMLSyntaxError as e:
                    job.pyprint(
                        "Couldn't validate the events XML file",
                        xml_path,
                        "using the PREMIS XML schema",
                        premis_xsd,
                    )
                    raise e
                file_queryset = File.objects.filter(transfer_id=transfer_uuid)
                with transaction.atomic():
                    for event in parse_events_xml(xml_path, file_queryset):
                        job.pyprint(
                            "Imported PREMIS event and assigned UUID", event.uuid
                        )
            else:
                job.pyprint("No events XML file found at path: ", xml_path)
        job.set_status(0)
